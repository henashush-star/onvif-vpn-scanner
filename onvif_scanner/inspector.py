from onvif import ONVIFCamera
from .models import CameraInfo, StreamProfile, PTZInfo, PTZStatus, PTZLimits
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

class CameraInspector:
    def __init__(self, ip: str, user: str, password: str, port: int = 80):
        self.ip = ip
        self.user = user
        self.password = password
        self.port = port
        self.camera = None

    def connect(self):
        try:
            self.camera = ONVIFCamera(self.ip, self.port, self.user, self.password)
        except Exception as e:
            logger.error(f"Failed to connect to {self.ip}: {e}")
            raise

    def get_device_info(self) -> CameraInfo:
        if not self.camera:
            self.connect()

        try:
            devicemgmt = self.camera.create_devicemgmt_service()
            device_info = devicemgmt.GetDeviceInformation()

            return CameraInfo(
                ip=self.ip,
                manufacturer=getattr(device_info, 'Manufacturer', 'Unknown'),
                model=getattr(device_info, 'Model', 'Unknown'),
                firmware=getattr(device_info, 'FirmwareVersion', 'Unknown'),
                serial=getattr(device_info, 'SerialNumber', 'Unknown'),
                inspection_status="ok"
            )
        except Exception as e:
            logger.error(f"Failed to get device info for {self.ip}: {e}")
            return CameraInfo(
                ip=self.ip,
                manufacturer="Unknown",
                model="Unknown",
                firmware="Unknown",
                serial="Unknown",
                inspection_status="incomplete_data"
            )

    def get_profiles(self) -> List[StreamProfile]:
        if not self.camera:
            self.connect()

        profiles_list = []
        try:
            media = self.camera.create_media_service()
            profiles = media.GetProfiles()

            for profile in profiles:
                token = profile.token
                name = profile.Name
                rtsp_uri = "Unknown"

                try:
                    # Setup StreamSetup
                    obj = media.create_type('GetStreamUri')
                    obj.StreamSetup = {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}}
                    obj.ProfileToken = token
                    res = media.GetStreamUri(obj)
                    rtsp_uri = res.Uri
                except Exception as e:
                    logger.debug(f"Failed to get URI for profile {name}: {e}")

                profiles_list.append(StreamProfile(name=name, token=token, rtsp_uri=rtsp_uri))

        except Exception as e:
            logger.error(f"Failed to get profiles for {self.ip}: {e}")

        return profiles_list

    def get_ptz_status(self) -> PTZInfo:
        if not self.camera:
            self.connect()

        supported = False
        status = None
        limits = None

        try:
            ptz = self.camera.create_ptz_service()
            supported = True

            media = self.camera.create_media_service()
            profiles = media.GetProfiles()
            if profiles:
                profile_token = profiles[0].token

                # Get Status
                try:
                    ptz_status = ptz.GetStatus({'ProfileToken': profile_token})
                    if ptz_status and hasattr(ptz_status, 'Position'):
                        pos = ptz_status.Position
                        pan = pos.PanTilt.x if hasattr(pos, 'PanTilt') and pos.PanTilt else 0.0
                        tilt = pos.PanTilt.y if hasattr(pos, 'PanTilt') and pos.PanTilt else 0.0
                        zoom = pos.Zoom.x if hasattr(pos, 'Zoom') and pos.Zoom else 0.0
                        status = PTZStatus(pan=pan, tilt=tilt, zoom=zoom)
                except Exception:
                    pass

                # Get Limits
                # This is complex because we need configuration token
                try:
                    # Assume profile has PTZConfiguration
                    if hasattr(profiles[0], 'PTZConfiguration') and profiles[0].PTZConfiguration:
                        conf_token = profiles[0].PTZConfiguration.token
                        ptz_conf_opts = ptz.GetConfigurationOptions({'ConfigurationToken': conf_token})

                        pan_min, pan_max = -1.0, 1.0
                        tilt_min, tilt_max = -1.0, 1.0
                        zoom_min, zoom_max = 0.0, 1.0

                        if hasattr(ptz_conf_opts, 'Spaces'):
                            spaces = ptz_conf_opts.Spaces
                            if hasattr(spaces, 'AbsolutePanTiltPositionSpace') and spaces.AbsolutePanTiltPositionSpace:
                                space = spaces.AbsolutePanTiltPositionSpace[0]
                                pan_min = space.XRange.Min
                                pan_max = space.XRange.Max
                                tilt_min = space.YRange.Min
                                tilt_max = space.YRange.Max

                            if hasattr(spaces, 'AbsoluteZoomPositionSpace') and spaces.AbsoluteZoomPositionSpace:
                                space = spaces.AbsoluteZoomPositionSpace[0]
                                zoom_min = space.XRange.Min
                                zoom_max = space.XRange.Max

                        limits = PTZLimits(pan=(pan_min, pan_max), tilt=(tilt_min, tilt_max), zoom=(zoom_min, zoom_max))
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"PTZ not supported or failed for {self.ip}: {e}")
            supported = False

        return PTZInfo(supported=supported, status=status, limits=limits)
