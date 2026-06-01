import bpy


class MultiuserDataChanger:
    """Helper class to be used when changing data of objects with multi-user data.

    Usage:

    Use make_object_data_single_user to create a copy of the current linked data
    and to assign it to the active object.

    Use link_new_object_data_to_instances to assign the new data to the
    other instances."""

    def __init__(self, ob: bpy.types.Object) -> None:
        self._ob = ob
        self._old_data_name: str | None = None
        self._new_data_name: str | None = None

    def get_data_collection(
        self,
    ) -> bpy.types.BlendDataMeshes | bpy.types.BlendDataCurves:
        assert self._ob.type in {'MESH', 'CURVE', 'SURFACE', 'FONT'}, "Unsupported object type"
        if self._ob.type == 'MESH':
            return bpy.data.meshes
        return bpy.data.curves

    def make_object_data_single_user(self) -> None:
        assert self._ob.data is not None
        new_data = self._ob.data.copy()
        self._old_data_name = self._ob.data.name
        self._new_data_name = new_data.name
        self._ob.data = new_data

    def link_new_object_data_to_instances(self) -> None:
        assert self._old_data_name is not None
        assert self._new_data_name is not None
        instances = [ob for ob in bpy.data.objects if ob.data and ob.data.name == self._old_data_name]
        data_collection = self.get_data_collection()

        for ob in instances:
            ob.data = data_collection[self._new_data_name]

        data = data_collection[self._old_data_name]
        if isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)
        else:
            bpy.data.curves.remove(data)
