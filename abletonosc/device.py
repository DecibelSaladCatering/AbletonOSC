from typing import Tuple, Any
from .handler import AbletonOSCHandler

class DeviceHandler(AbletonOSCHandler):
    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "device"

    def init_api(self):
        def create_device_callback(func, *args, include_ids: bool = False):
            def device_callback(params: Tuple[Any]):
                track_index, device_index = int(params[0]), int(params[1])
                device = self.song.tracks[track_index].devices[device_index]
                if (include_ids):
                    rv = func(device, *args, params[0:])
                else:
                    rv = func(device, *args, params[2:])

                if rv is not None:
                    return (track_index, device_index, *rv)

            return device_callback

        methods = [
        ]
        properties_r = [
            "class_name",
            "name",
            "type"
        ]
        properties_rw = [
        ]

        for method in methods:
            self.osc_server.add_handler("/live/device/%s" % method,
                                        create_device_callback(self._call_method, method))

        for prop in properties_r + properties_rw:
            self.osc_server.add_handler("/live/device/get/%s" % prop,
                                        create_device_callback(self._get_property, prop))
            self.osc_server.add_handler("/live/device/start_listen/%s" % prop,
                                        create_device_callback(self._start_listen, prop))
            self.osc_server.add_handler("/live/device/stop_listen/%s" % prop,
                                        create_device_callback(self._stop_listen, prop))
        for prop in properties_rw:
            self.osc_server.add_handler("/live/device/set/%s" % prop,
                                        create_device_callback(self._set_property, prop))

        #--------------------------------------------------------------------------------
        # Device: Get/set parameter lists
        #--------------------------------------------------------------------------------
        def device_get_num_parameters(device, params: Tuple[Any] = ()):
            return len(device.parameters),

        def device_get_parameters_name(device, params: Tuple[Any] = ()):
            return tuple(parameter.name for parameter in device.parameters)

        def device_get_parameters_value(device, params: Tuple[Any] = ()):
            return tuple(parameter.value for parameter in device.parameters)

        def device_get_parameters_min(device, params: Tuple[Any] = ()):
            return tuple(parameter.min for parameter in device.parameters)

        def device_get_parameters_max(device, params: Tuple[Any] = ()):
            return tuple(parameter.max for parameter in device.parameters)

        def device_get_parameters_is_quantized(device, params: Tuple[Any] = ()):
            return tuple(parameter.is_quantized for parameter in device.parameters)

        def device_set_parameters_value(device, params: Tuple[Any] = ()):
            for index, value in enumerate(params):
                device.parameters[index].value = value

        self.osc_server.add_handler("/live/device/get/num_parameters", create_device_callback(device_get_num_parameters))
        self.osc_server.add_handler("/live/device/get/parameters/name", create_device_callback(device_get_parameters_name))
        self.osc_server.add_handler("/live/device/get/parameters/value", create_device_callback(device_get_parameters_value))
        self.osc_server.add_handler("/live/device/get/parameters/min", create_device_callback(device_get_parameters_min))
        self.osc_server.add_handler("/live/device/get/parameters/max", create_device_callback(device_get_parameters_max))
        self.osc_server.add_handler("/live/device/get/parameters/is_quantized", create_device_callback(device_get_parameters_is_quantized))
        self.osc_server.add_handler("/live/device/set/parameters/value", create_device_callback(device_set_parameters_value))

        #--------------------------------------------------------------------------------
        # Device: Get/set individual parameters
        #--------------------------------------------------------------------------------
        def device_get_parameter_value(device, params: Tuple[Any] = ()):
            # Cast to ints so that we can tolerate floats from interfaces such as TouchOSC
            # that send floats by default.
            # https://github.com/ideoforms/AbletonOSC/issues/33
            param_index = int(params[0])
            return param_index, device.parameters[param_index].value
        
        # Uses str_for_value method to return the UI-friendly version of a parameter value (ex: "2500 Hz")
        def device_get_parameter_value_string(device, params: Tuple[Any] = ()):
            param_index = int(params[0])
            return param_index, device.parameters[param_index].str_for_value(device.parameters[param_index].value)
        
        def device_get_parameter_value_listener(device, params: Tuple[Any] = ()):

            def property_changed_callback():
                value = device.parameters[params[2]].value
                self.logger.info("Property %s changed of %s %s: %s" % ('value', 'device parameter', str(params), value))
                self.osc_server.send("/live/device/get/parameter/value", (*params, value,))

                value_string = device.parameters[params[2]].str_for_value(device.parameters[params[2]].value)
                self.logger.info("Property %s changed of %s %s: %s" % ('value_string', 'device parameter', str(params), value_string))
                self.osc_server.send("/live/device/get/parameter/value_string", (*params, value_string,))

            listener_key = ('device_parameter_value', tuple(params))
            if listener_key in self.listener_functions:
               device_get_parameter_remove_value_listener(device, params)

            self.logger.info("Adding listener for %s %s, property: %s" % ('device parameter', str(params), 'value'))
            device.parameters[params[2]].add_value_listener(property_changed_callback)
            self.listener_functions[listener_key] = property_changed_callback

            property_changed_callback()

        def device_get_parameter_remove_value_listener(device, params: Tuple[Any] = ()):
            listener_key = ('device_parameter_value', tuple(params))
            if listener_key in self.listener_functions:
                self.logger.info("Removing listener for %s %s, property %s" % (self.class_identifier, str(params), 'value'))
                listener_function = self.listener_functions[listener_key]
                device.parameters[params[2]].remove_value_listener(listener_function)
                del self.listener_functions[listener_key]
            else:
                self.logger.warning("No listener function found for property: %s (%s)" % (prop, str(params)))

        def device_set_parameter_value(device, params: Tuple[Any] = ()):
            param_index, param_value = params[:2]
            param_index = int(param_index)
            device.parameters[param_index].value = param_value

        def device_get_parameter_name(device, params: Tuple[Any] = ()):
            param_index = int(params[0])
            return param_index, device.parameters[param_index].name

        self.osc_server.add_handler("/live/device/get/parameter/value", create_device_callback(device_get_parameter_value))
        self.osc_server.add_handler("/live/device/get/parameter/value_string", create_device_callback(device_get_parameter_value_string))
        self.osc_server.add_handler("/live/device/set/parameter/value", create_device_callback(device_set_parameter_value))
        self.osc_server.add_handler("/live/device/get/parameter/name", create_device_callback(device_get_parameter_name))
        self.osc_server.add_handler("/live/device/start_listen/parameter/value", create_device_callback(device_get_parameter_value_listener, include_ids = True))
        self.osc_server.add_handler("/live/device/stop_listen/parameter/value", create_device_callback(device_get_parameter_remove_value_listener, include_ids = True))

        #--------------------------------------------------------------------------------
        # TouchLive patch: chain-aware device addressing
        # Path = [topDeviceIndex, chainIndex, nestedDeviceIndex, ...] alternating
        # device/chain levels (racks expose .chains, chains expose .devices).
        #--------------------------------------------------------------------------------
        def resolve_device(track_index, path):
            device = self.song.tracks[track_index].devices[path[0]]
            for idx in path[1:]:
                if hasattr(device, "chains"):
                    device = device.chains[idx]
                else:
                    device = device.devices[idx]
            return device

        def path_callback(extra_args, func):
            def wrapper(params: Tuple[Any]):
                track_index = int(params[0])
                path = tuple(int(p) for p in params[1:len(params) - extra_args]) if extra_args > 0 else tuple(int(p) for p in params[1:])
                device = resolve_device(track_index, path)
                args = params[len(params) - extra_args:] if extra_args > 0 else ()
                rv = func(device, args)
                if rv is None:
                    return (track_index, *path)
                return (track_index, *path, *rv)
            return wrapper

        def path_get_parameters_name(device, args):
            return tuple(parameter.name for parameter in device.parameters)

        def path_get_parameters_value(device, args):
            return tuple(parameter.value for parameter in device.parameters)

        def path_get_parameters_min(device, args):
            return tuple(parameter.min for parameter in device.parameters)

        def path_get_parameters_max(device, args):
            return tuple(parameter.max for parameter in device.parameters)

        def path_get_name(device, args):
            return (device.name,)

        def path_set_parameter_value(device, args):
            param_index, param_value = args[:2]
            device.parameters[int(param_index)].value = param_value

        def path_get_parameter_value(device, args):
            param_index = int(args[0])
            return param_index, device.parameters[param_index].value

        def path_parameter_value_listener(params: Tuple[Any]):
            track_index = int(params[0])
            path = tuple(int(p) for p in params[1:-1])
            param_index = int(params[-1])
            device = resolve_device(track_index, path)

            def property_changed_callback():
                value = device.parameters[param_index].value
                self.osc_server.send("/live/device/path/get/parameter/value", (track_index, *path, param_index, value))

            listener_key = ('device_path_parameter_value', (track_index, path, param_index))
            if listener_key in self.listener_functions:
                path_parameter_remove_value_listener(params)

            device.parameters[param_index].add_value_listener(property_changed_callback)
            self.listener_functions[listener_key] = property_changed_callback
            self.listener_objects[listener_key] = device.parameters[param_index]
            property_changed_callback()

        def path_parameter_remove_value_listener(params: Tuple[Any]):
            track_index = int(params[0])
            path = tuple(int(p) for p in params[1:-1])
            param_index = int(params[-1])
            listener_key = ('device_path_parameter_value', (track_index, path, param_index))
            if listener_key in self.listener_functions:
                listener_function = self.listener_functions[listener_key]
                resolve_device(track_index, path).parameters[param_index].remove_value_listener(listener_function)
                del self.listener_functions[listener_key]
                del self.listener_objects[listener_key]
            else:
                self.logger.warning("No path listener found for: %s" % str(params))

        self.osc_server.add_handler("/live/device/path/get/parameters/name", path_callback(0, path_get_parameters_name))
        self.osc_server.add_handler("/live/device/path/get/parameters/value", path_callback(0, path_get_parameters_value))
        self.osc_server.add_handler("/live/device/path/get/parameters/min", path_callback(0, path_get_parameters_min))
        self.osc_server.add_handler("/live/device/path/get/parameters/max", path_callback(0, path_get_parameters_max))
        self.osc_server.add_handler("/live/device/path/get/name", path_callback(0, path_get_name))
        self.osc_server.add_handler("/live/device/path/set/parameter/value", path_callback(2, path_set_parameter_value))
        self.osc_server.add_handler("/live/device/path/get/parameter/value", path_callback(1, path_get_parameter_value))
        self.osc_server.add_handler("/live/device/path/start_listen/parameter/value", path_parameter_value_listener)
        self.osc_server.add_handler("/live/device/path/stop_listen/parameter/value", path_parameter_remove_value_listener)
