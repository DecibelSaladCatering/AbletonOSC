from functools import partial
from typing import Optional, Tuple, Any
from .handler import AbletonOSCHandler

class ViewHandler(AbletonOSCHandler):
    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "view"

    def init_api(self):
        def get_selected_scene(params: Optional[Tuple] = ()):
            return (list(self.song.scenes).index(self.song.view.selected_scene),)

        def get_selected_track(params: Optional[Tuple] = ()):
            return (list(self.song.tracks).index(self.song.view.selected_track),)

        def get_selected_clip(params: Optional[Tuple] = ()):
            return (get_selected_track()[0], get_selected_scene()[0])

        def set_selected_scene(params: Optional[Tuple] = ()):
            self.song.view.selected_scene = self.song.scenes[params[0]]

        def set_selected_track(params: Optional[Tuple] = ()):
            self.song.view.selected_track = self.song.tracks[params[0]]

        def set_selected_clip(params: Optional[Tuple] = ()):
            set_selected_track((params[0],))
            set_selected_scene((params[1],))

        def set_selected_device(params: Optional[Tuple] = ()):
            device = self.song.tracks[params[0]].devices[params[1]]
            self.song.view.select_device(device)
            return params[0], params[1]

        def get_selected_device(params: Optional[Tuple] = ()):
            # Legacy flat reply. When no device is focused in the track view, reply
            # with device index -1 instead of raising (which used to kill the reply).
            track_index = get_selected_track()[0]
            device = self.song.view.selected_track.view.selected_device
            if device is None:
                return (track_index, -1)
            try:
                device_index = list(self.song.view.selected_track.devices).index(device)
            except ValueError:
                # Focused device is nested inside a rack — not addressable flat.
                return (track_index, -1)
            return (track_index, device_index)

        #--------------------------------------------------------------------------------
        # TouchLive patch: nested-safe selected-device info (path from canonical parents)
        #--------------------------------------------------------------------------------
        def _device_path_for(device, track):
            path = []
            obj = device
            while obj != track:
                parent = obj.canonical_parent
                if parent is None:
                    return None
                if hasattr(parent, "devices"):
                    path.insert(0, list(parent.devices).index(obj))
                else:
                    path.insert(0, list(parent.chains).index(obj))
                obj = parent
            return tuple(path)

        def selected_device_info():
            track = self.song.view.selected_track
            device = track.view.selected_device
            if device is None:
                return None
            path = _device_path_for(device, track)
            if path is None:
                return None
            return (list(self.song.tracks).index(track), *path, device.class_name, device.name)

        def get_selected_device_info(params: Optional[Tuple] = ()):
            return selected_device_info()

        def start_listen_selected_device(params: Optional[Tuple] = ()):
            def device_changed():
                info = selected_device_info()
                if info is not None:
                    self.osc_server.send("/live/view/get/selected_device_info", info)

            def track_changed():
                # The device selection lives on the track's view — re-register on track change.
                device_key = ("selected_device_info", ())
                if device_key in self.listener_functions:
                    old_callback = self.listener_functions[device_key]
                    self.song.view.selected_track.view.remove_selected_device_listener(old_callback)
                self.song.view.selected_track.view.add_selected_device_listener(device_changed)
                self.listener_functions[device_key] = device_changed
                device_changed()

            track_key = ("selected_device_track_hook", ())
            if track_key not in self.listener_functions:
                self.song.view.add_selected_track_listener(track_changed)
                self.listener_functions[track_key] = track_changed
            track_changed()

        def stop_listen_selected_device(params: Optional[Tuple] = ()):
            device_key = ("selected_device_info", ())
            if device_key in self.listener_functions:
                old_callback = self.listener_functions[device_key]
                self.song.view.selected_track.view.remove_selected_device_listener(old_callback)
                del self.listener_functions[device_key]
            track_key = ("selected_device_track_hook", ())
            if track_key in self.listener_functions:
                self.song.view.remove_selected_track_listener(self.listener_functions[track_key])
                del self.listener_functions[track_key]

        #--------------------------------------------------------------------------------
        # TouchLive patch: selected-parameter capture (mapping pathway)
        #--------------------------------------------------------------------------------
        def _track_for_device(device):
            obj = device
            while obj is not None:
                try:
                    list(self.song.tracks).index(obj)
                    return obj
                except ValueError:
                    obj = obj.canonical_parent
            return None

        def selected_parameter_info():
            param = self.song.view.selected_parameter
            if param is None:
                return None
            device = param.canonical_parent
            if device is None:
                return None
            track = _track_for_device(device)
            if track is None:
                return None
            path = _device_path_for(device, track)
            if path is None:
                return None
            try:
                param_index = list(device.parameters).index(param)
            except ValueError:
                return None
            return (
                list(self.song.tracks).index(track), *path, param_index,
                param.name, param.value, param.min, param.max,
            )

        def get_selected_parameter(params: Optional[Tuple] = ()):
            return selected_parameter_info()

        def start_listen_selected_parameter(params: Optional[Tuple] = ()):
            def parameter_changed():
                info = selected_parameter_info()
                if info is not None:
                    self.osc_server.send("/live/view/get/selected_parameter", info)

            listener_key = ("selected_parameter_info", ())
            if listener_key in self.listener_functions:
                stop_listen_selected_parameter()
            self.song.view.add_selected_parameter_listener(parameter_changed)
            self.listener_functions[listener_key] = parameter_changed
            parameter_changed()

        def stop_listen_selected_parameter(params: Optional[Tuple] = ()):
            listener_key = ("selected_parameter_info", ())
            if listener_key in self.listener_functions:
                self.song.view.remove_selected_parameter_listener(self.listener_functions[listener_key])
                del self.listener_functions[listener_key]

        self.osc_server.add_handler("/live/view/get/selected_scene", get_selected_scene)
        self.osc_server.add_handler("/live/view/get/selected_track", get_selected_track)
        self.osc_server.add_handler("/live/view/get/selected_clip", get_selected_clip)
        self.osc_server.add_handler("/live/view/get/selected_device", get_selected_device)
        self.osc_server.add_handler("/live/view/set/selected_scene", set_selected_scene)
        self.osc_server.add_handler("/live/view/set/selected_track", set_selected_track)
        self.osc_server.add_handler("/live/view/set/selected_clip", set_selected_clip)
        self.osc_server.add_handler("/live/view/set/selected_device", set_selected_device)

        self.osc_server.add_handler("/live/view/get/selected_device_info", get_selected_device_info)
        self.osc_server.add_handler("/live/view/start_listen/selected_device", start_listen_selected_device)
        self.osc_server.add_handler("/live/view/stop_listen/selected_device", stop_listen_selected_device)
        self.osc_server.add_handler("/live/view/get/selected_parameter", get_selected_parameter)
        self.osc_server.add_handler("/live/view/start_listen/selected_parameter", start_listen_selected_parameter)
        self.osc_server.add_handler("/live/view/stop_listen/selected_parameter", stop_listen_selected_parameter)

        self.osc_server.add_handler('/live/view/start_listen/selected_scene', partial(self._start_listen, self.song.view, "selected_scene", getter=get_selected_scene))
        self.osc_server.add_handler('/live/view/start_listen/selected_track', partial(self._start_listen, self.song.view, "selected_track", getter=get_selected_track))
        self.osc_server.add_handler('/live/view/stop_listen/selected_scene', partial(self._stop_listen, self.song.view, "selected_scene"))
        self.osc_server.add_handler('/live/view/stop_listen/selected_track', partial(self._stop_listen, self.song.view, "selected_track"))
