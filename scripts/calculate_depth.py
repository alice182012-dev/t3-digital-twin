import os
import re
import shutil
import uuid
import numpy as np
import billiard as multiprocessing
from datetime import datetime, timedelta
from osgeo import gdal
from threedidepth import calculate_waterdepth
from threedigrid.admin.gridresultadmin import GridH5ResultAdmin

import fiona
import fiona.vfs

if not hasattr(fiona, 'path'):
    fiona.path = fiona.vfs


CLEAN_DATA = True

# Corrupt/truncated raster detection (T4). A genuine per-timestep depth
# GeoTIFF for this model is never this small, and a fully-valid raster is
# never entirely NoData; a file that violates either bound is treated as a
# cycle failure rather than silently published. Bounds are placeholders —
# recalibrate from a known-good reference set before relying on this in
# production.
MIN_DEPTH_TIF_SIZE_BYTES = int(os.getenv("DEPTH_TIF_MIN_SIZE_BYTES", "1024"))
MAX_DEPTH_TIF_NODATA_RATIO = float(os.getenv("DEPTH_TIF_MAX_NODATA_RATIO", "0.999"))


def validate_depth_raster(tif_path):
    """Reject a depth GeoTIFF that is corrupt/truncated or almost entirely NoData.

    Checked on the raw output of calculate_waterdepth(), before
    get_time_from_tif_and_clean() rewrites NoData/negative/out-of-range
    values to 0 (which would otherwise make a genuinely corrupt raster look
    like a normal, mostly-dry timestep). Returns (is_valid, reason).
    """
    try:
        size_bytes = os.path.getsize(tif_path)
        if size_bytes < MIN_DEPTH_TIF_SIZE_BYTES:
            return False, f"file too small ({size_bytes}B < {MIN_DEPTH_TIF_SIZE_BYTES}B)"

        ds = gdal.Open(tif_path, 0)
        if ds is None:
            return False, "unreadable by GDAL"
        band = ds.GetRasterBand(1)
        data = band.ReadAsArray()
        nodata_val = band.GetNoDataValue()
        ds = None

        if data is None or data.size == 0:
            return False, "no pixel data"

        if nodata_val is not None:
            if np.isnan(nodata_val):
                nodata_count = np.isnan(data).sum()
            else:
                nodata_count = (data == nodata_val).sum()
            nodata_ratio = nodata_count / data.size
            if nodata_ratio > MAX_DEPTH_TIF_NODATA_RATIO:
                return False, f"NoData ratio too high ({nodata_ratio:.3%})"

        return True, None
    except Exception as e:
        return False, f"validation error: {e}"


def get_time_from_tif_and_clean(tif_path):
    """Đọc giờ từ TIF (UTC) -> cộng 7 tiếng -> Làm sạch dữ liệu"""
    time_str_vn = None
    try:
        # Read-only: rewriting pixel data in place on an already-compressed
        # (DEFLATE) TIFF is unreliable in GDAL/libtiff (recompressed strips
        # rarely match the original byte size, corrupting strip offsets), so
        # any cleanup below writes a fresh file instead of updating in place.
        ds = gdal.Open(tif_path, 0)
        if ds is None:
            return None
        band = ds.GetRasterBand(1)

        desc = band.GetDescription()
        match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", desc)
        if match:
            dt_utc = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
            dt_vn = dt_utc + timedelta(hours=7)
            time_str_vn = dt_vn.strftime("%Y%m%d_%H%M%S")
            desc = desc.replace(match.group(1), dt_vn.strftime("%Y-%m-%d %H:%M:%S"))

        if CLEAN_DATA:
            data = band.ReadAsArray()
            nodata_val = band.GetNoDataValue()
            geotransform = ds.GetGeoTransform()
            projection = ds.GetProjection()
            ds = None

            if data.max() > 0:
                if nodata_val is not None:
                    if np.isnan(nodata_val):
                        data[np.isnan(data)] = 0
                    else:
                        data[data == nodata_val] = 0
                        if nodata_val > 1000:
                            data[data > 1000] = 0
                data[data < 0] = 0
                data[data > 100] = 0

                tmp_path = tif_path + ".clean.tmp"
                driver = gdal.GetDriverByName("GTiff")
                out_ds = driver.Create(
                    tmp_path, data.shape[1], data.shape[0], 1, gdal.GDT_Float32,
                    options=["COMPRESS=DEFLATE"],
                )
                out_ds.SetGeoTransform(geotransform)
                out_ds.SetProjection(projection)
                out_band = out_ds.GetRasterBand(1)
                out_band.WriteArray(data)
                out_band.SetNoDataValue(0)
                out_band.SetDescription(desc)
                out_ds.FlushCache()
                out_ds = None

                os.replace(tmp_path, tif_path)
        else:
            ds = None
    except Exception as e:
        print(f"⚠️ Warning {os.path.basename(tif_path)}: {e}")
    return time_str_vn


def process_single_step(args):
    """Worker chạy trên từng process (đa tiến trình)"""
    step_index, grid_path, nc_path, dem_path, output_dir = args

    temp_filename = f"temp_{step_index:04d}.tif"
    temp_path = os.path.join(output_dir, temp_filename)

    try:

        calculate_waterdepth(
            gridadmin_path=grid_path,
            results_3di_path=nc_path,
            dem_path=dem_path,
            waterdepth_path=temp_path,
            calculation_steps=[step_index],
        )

        is_valid, invalid_reason = validate_depth_raster(temp_path)
        if not is_valid:
            return f"❌ Step {step_index}: corrupt/undersized raster ({invalid_reason})"

        timestamp_name = get_time_from_tif_and_clean(temp_path)
        if timestamp_name:
            final_name = f"depth_{timestamp_name}.tif"
            final_path = os.path.join(output_dir, final_name)
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(temp_path, final_path)
            return f"✅ {final_name}"
        else:
            # No timestamp match in the band description: name it clearly and
            # move it out of the temp_*.tif naming so it never ships into the
            # final output dir looking like an in-progress/orphaned file.
            final_name = f"notime_step{step_index:04d}.tif"
            final_path = os.path.join(output_dir, final_name)
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(temp_path, final_path)
            return f"⚠️ {final_name} (No Time)"
    except Exception as e:
        return f"❌ Step {step_index}: {e}"


def run_calculate_depth(grid_path, nc_path, dem_path, output_dir):

    # Unique per invocation (not just per nc file) so a stale/orphaned process
    # from a previously killed run can never write into the same directory a
    # new run is using.
    temp_dir_name = f"_processing_{os.path.splitext(os.path.basename(nc_path))[0]}_{uuid.uuid4().hex[:8]}"
    current_output_dir = os.path.join(output_dir, temp_dir_name)

    os.makedirs(current_output_dir)
    print(f"📂 Created Output Dir: {current_output_dir}")

    try:
        ga = GridH5ResultAdmin(grid_path, nc_path)
        total_steps = len(ga.nodes.timestamps)
        ga = None
        print(f"🔄 Total Steps: {total_steps}")
    except Exception as e:
        print(f"❌ Error reading inputs: {e}")
        raise e

    # Step 0 is 3Di's placeholder t=0 record (Mesh2D_s1 is nodata for most/all
    # nodes regardless of cold-start or hotstart) and never yields a usable
    # depth raster, so skip it in favor of the first real integration step.
    step_indices = range(1, total_steps) if total_steps > 1 else range(total_steps)

    # Đóng gói tham số cho từng process
    tasks = [(i, grid_path, nc_path, dem_path, current_output_dir) for i in step_indices]
    
    # Sử dụng tối đa CPU core có sẵn thay vì giới hạn 8
    try:
        # Lấy số CPU được phép sử dụng (trong container)
        default_workers = len(os.sched_getaffinity(0))
    except AttributeError:
        default_workers = multiprocessing.cpu_count()
    max_workers = int(os.getenv("MAX_WORKERS", str(default_workers)))

    print(f"🚀 Calculating on {max_workers} processes (Multiprocessing)...")
    # Sử dụng billiard.Pool, một nhánh của multiprocessing.Pool, an toàn để sử dụng
    # trong các tiến trình daemon (như Celery workers) mà không cần các giải pháp tạm thời.
    pool = multiprocessing.Pool(processes=max_workers)
    try:
        results = pool.map(process_single_step, tasks)
        for res in results:
            print(res)
    finally:
        pool.close()
        pool.join()

    # Orchestration-only failure surfacing (T13): process_single_step never
    # raises out of the pool, it returns a "❌ ..." string per failed
    # timestep. Without this check a cycle where some timesteps failed still
    # reports success with an incomplete depth-tif set.
    failures = [res for res in results if res.startswith("❌")]
    if failures:
        raise RuntimeError(
            f"{len(failures)}/{len(results)} depth timesteps failed: " + "; ".join(failures)
        )

    depth_files = sorted(
        f for f in os.listdir(current_output_dir)
        if f.startswith("depth_") and f.endswith(".tif")
    )

    if depth_files:
        start_stamp = depth_files[0][len("depth_"):-len(".tif")]
        end_stamp = depth_files[-1][len("depth_"):-len(".tif")]
        date_part, start_time = start_stamp.split("_")
        _, end_time = end_stamp.split("_")
        final_dir_name = f"depth_{date_part}_{start_time}_{end_time}"
    else:
        final_dir_name = f"depth_{datetime.now().strftime('%Y%m%d_%H%M%S')}_empty"

    final_output_dir = os.path.join(output_dir, final_dir_name)
    if os.path.exists(final_output_dir):
        shutil.rmtree(final_output_dir)
    os.rename(current_output_dir, final_output_dir)

    print(f"🎉 Calculate Depth Done! Saved to: {final_output_dir}")
    return final_output_dir
