"""The 3Di NetCDF variables this pipeline stores, and their catalog ids.

Imports nothing, so the DDL script and the backfill script can read the id
ordering without pulling in xarray, numpy or pandas.
"""

VARIABLE_MAPPING = {
    "Mesh2D_s1": {
        "mesh_type": "2D",
        "element_type": "node",
        "id_var": "Mesh2DNode_id",
        "x_var": "Mesh2DFace_xcc",
        "y_var": "Mesh2DFace_ycc",
    },
    "Mesh2D_vol": {
        "mesh_type": "2D",
        "element_type": "node",
        "id_var": "Mesh2DNode_id",
        "x_var": "Mesh2DFace_xcc",
        "y_var": "Mesh2DFace_ycc",
    },
    "Mesh2D_rain": {
        "mesh_type": "2D",
        "element_type": "node",
        "id_var": "Mesh2DNode_id",
        "x_var": "Mesh2DFace_xcc",
        "y_var": "Mesh2DFace_ycc",
    },
    "Mesh2D_ucx": {
        "mesh_type": "2D",
        "element_type": "node",
        "id_var": "Mesh2DNode_id",
        "x_var": "Mesh2DFace_xcc",
        "y_var": "Mesh2DFace_ycc",
    },
    "Mesh2D_ucy": {
        "mesh_type": "2D",
        "element_type": "node",
        "id_var": "Mesh2DNode_id",
        "x_var": "Mesh2DFace_xcc",
        "y_var": "Mesh2DFace_ycc",
    },
    "Mesh2D_q": {
        "mesh_type": "2D",
        "element_type": "line",
        "id_var": "Mesh2DLine_id",
        "x_var": "Mesh2DLine_xcc",
        "y_var": "Mesh2DLine_ycc",
    },
    "Mesh1D_s1": {
        "mesh_type": "1D",
        "element_type": "node",
        "id_var": "Mesh1DNode_id",
        "x_var": "Mesh1DNode_xcc",
        "y_var": "Mesh1DNode_ycc",
    },
    "Mesh1D_q": {
        "mesh_type": "1D",
        "element_type": "line",
        "id_var": "Mesh1DLine_id",
        "x_var": "Mesh1DLine_xcc",
        "y_var": "Mesh1DLine_ycc",
    },
}

# Insertion order of VARIABLE_MAPPING is the only definition of the catalog ids.
# Reordering or inserting a key renumbers the ids of every variable after it and
# orphans the netcdf_values rows already written against the old numbering.
VARIABLE_CATALOG = tuple(
    (index, variable_name, mapping["mesh_type"], mapping["element_type"])
    for index, (variable_name, mapping) in enumerate(VARIABLE_MAPPING.items(), start=1)
)
