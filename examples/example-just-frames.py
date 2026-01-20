import datetime
import os
from pathlib import Path

from aind_behavior_services.rig import harp, cameras
from aind_behavior_services.common import Rect
from aind_behavior_services.session import AindBehaviorSessionModel

from aind_behavior_just_frames.rig import AindJustFramesRig, SatelliteRig, NetworkConfig

EXPOSURE = 4000
GAIN_MAIN = 10
GAIN_SLAVE = 14
FPS = 200


def define_camera(serial_number: str, gain: float, exposure: int = EXPOSURE):
    video_writer = cameras.VideoWriterFfmpeg(
        frame_rate=FPS,
        container_extension="mp4",
        # input and output arguments can be overridden by the user
    )
    default_roi = Rect(width=1200, height=800, x=120, y=140)
    # default_roi = cameras
    return cameras.SpinnakerCamera(
        serial_number=serial_number,
        binning=1,
        exposure=exposure,
        gain=gain,
        video_writer=video_writer,
        adc_bit_depth=cameras.SpinnakerCameraAdcBitDepth.ADC10BIT,
        region_of_interest=default_roi,
    )


def main(path_seed: str = "./local/{schema}.json"):
    this_session = AindBehaviorSessionModel(
        date=datetime.datetime.now(tz=datetime.timezone.utc),
        experiment="MotorObservatory+Fip",
        subject="809487",
        notes="Left Hemisphere",
        allow_dirty_repo=True,
        skip_hardware_validation=False,
        experimenter=["kenta.hagihara", "bruno.cruz"],
    )

    satallite = SatelliteRig(
        computer_name="W10DT714079",
        rig_name="satelite_rig",
        data_directory=Path(r"C:/Data"),
        triggered_camera_controller_0=cameras.CameraController[cameras.SpinnakerCamera](
            frame_rate=FPS,
            cameras={
                "Camera7": define_camera(
                    serial_number="23373894", exposure=EXPOSURE, gain=GAIN_SLAVE
                ),
                "Camera8": define_camera(
                    serial_number="23373899", exposure=EXPOSURE, gain=GAIN_SLAVE
                ),
                "Camera9": define_camera(
                    serial_number="23373898", exposure=EXPOSURE, gain=GAIN_SLAVE
                ),
                "Camera10": define_camera(
                    serial_number="23354678", exposure=EXPOSURE, gain=GAIN_SLAVE
                ),
                "Camera11": define_camera(
                    serial_number="23378574", exposure=EXPOSURE, gain=GAIN_SLAVE
                ),
            },
        ),
        zmq_trigger_config=NetworkConfig(address="10.128.49.106", port=5555),
        zmq_protocol_config=NetworkConfig(address="10.128.49.154", port=5556),
    )

    this_rig = AindJustFramesRig(
        data_directory=Path(r"D:/Data"),
        rig_name="MotorObservatory0000",
        computer_name="W10DT714163",
        triggered_camera_controller_0=cameras.CameraController[cameras.SpinnakerCamera](
            frame_rate=FPS,
            cameras={
                "Camera0": define_camera(
                    serial_number="23382593", exposure=EXPOSURE, gain=GAIN_MAIN
                ),
                "Camera1": define_camera(
                    serial_number="23382581", exposure=EXPOSURE, gain=GAIN_MAIN
                ),
                "Camera2": define_camera(
                    serial_number="23113712", exposure=EXPOSURE, gain=GAIN_MAIN
                ),
                "Camera3": define_camera(
                    serial_number="23381088", exposure=EXPOSURE, gain=GAIN_MAIN
                ),
                "Camera4": define_camera(
                    serial_number="20519746", exposure=EXPOSURE, gain=GAIN_MAIN
                ),
                "Camera5": define_camera(
                    serial_number="23382592", exposure=EXPOSURE, gain=GAIN_MAIN
                ),
                "Camera6": define_camera(
                    serial_number="23381091", exposure=EXPOSURE, gain=GAIN_MAIN
                ),
            },
        ),
        triggered_camera_controller_1=None,
        harp_behavior=harp.HarpBehavior(port_name="COM3"),
        satellite_rigs=[satallite],
        zmq_trigger_config=NetworkConfig(address="10.128.49.106", port=5555),
    )

    os.makedirs(os.path.dirname(path_seed), exist_ok=True)

    models = [this_session, this_rig, satallite]

    for model in models:
        with open(
            path_seed.format(schema=model.__class__.__name__), "w", encoding="utf-8"
        ) as f:
            f.write(model.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
