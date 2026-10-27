import os
import shutil
import tempfile


def localize_input(src, cache_dir):
    """Copy src into cache_dir and return the local path, or src if that fails.

    A copy is reused while its size and whole-second mtime match the source's.
    """
    try:
        src_stat = os.stat(src)
    except FileNotFoundError:
        return src

    local = os.path.join(cache_dir, os.path.basename(src))
    try:
        local_stat = os.stat(local)
        if local_stat.st_size == src_stat.st_size and int(local_stat.st_mtime) == int(src_stat.st_mtime):
            return local
    except FileNotFoundError:
        pass

    tmp_path = None
    try:
        os.makedirs(cache_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=cache_dir, prefix=f".{os.path.basename(src)}.")
        os.close(fd)
        shutil.copyfile(src, tmp_path)
        os.utime(tmp_path, (src_stat.st_atime, src_stat.st_mtime))
        # Atomic rename: a step running concurrently sees the old copy or the
        # new one, never a half-written file.
        os.replace(tmp_path, local)
        return local
    except Exception as e:
        if tmp_path is not None and os.path.exists(tmp_path):
            os.remove(tmp_path)
        print(f"⚠️ Could not copy {src} to {cache_dir}, reading it in place: {e}")
        return src
