import argparse
import datetime
import os
from pathlib import Path
from aind_behavior_services.rig.harp import HarpCuttlefishfip
from aind_behavior_services.session import AindBehaviorSessionModel

from aind_physiology_fip.data_mappers._acquisition import (
    ProtoAcquisitionDataSchema,
    _FipDataStreamMetadata,
)
from aind_physiology_fip.rig import (
    AindPhysioFipRig,
    FipCamera,
    FipTask,
    LightSource,
    LightSourceCalibration,
    Networking,
    Ports,
    RoiSettings,
    Point2f,
)


def mock_rig() -> AindPhysioFipRig:
    return AindPhysioFipRig(
        rig_name="MOT.01",
        data_directory=Path(r"D:/data"),
        computer_name="W10DT714163",
        camera_green_iso=FipCamera(
            serial_number="24521422", offset=Point2f(x=104, y=56)
        ),
        camera_red=FipCamera(serial_number="24521414", offset=Point2f(x=104, y=56)),
        light_source_blue=LightSource(
            power=10,
            calibration=LightSourceCalibration(
                power_lut={0.0: 0.0, 0.1: 10, 0.2: 20, 0.4: 40}
            ),
            task=FipTask(
                camera_port=Ports.IO0,  # GreenCamera + 470nm
                light_source_port=Ports.IO2,
            ),
        ),
        light_source_lime=LightSource(
            power=20,
            calibration=LightSourceCalibration(
                power_lut={0.0: 0.0, 0.1: 4.0, 0.2: 7.5, 0.4: 15, 0.6: 35}
            ),
            task=FipTask(
                camera_port=Ports.IO1,  # RedCamera + 560nm
                light_source_port=Ports.IO4,
            ),
        ),
        light_source_uv=LightSource(
            power=0.1,
            calibration=LightSourceCalibration(power_lut={0.0: 0.0, 0.1: 10, 0.2: 20}),
            task=FipTask(
                camera_port=Ports.IO0,  # GreenCamera + 410nm
                light_source_port=Ports.IO3,
            ),
        ),
        roi_settings=RoiSettings(),
        networking=Networking(),
        cuttlefish_fip=HarpCuttlefishfip(
            port_name="COM5",
        ),
    )


def mock_session() -> AindBehaviorSessionModel:
    return AindBehaviorSessionModel(
        date=datetime.datetime.now(tz=datetime.timezone.utc),
        experiment="MotorObservatory+Fip",
        subject="809487",
        notes="Left Hemisphere",
        allow_dirty_repo=True,
        skip_hardware_validation=False,
        experimenter=["kenta.hagihara", "bruno.cruz"],
    )


def make_mapped() -> ProtoAcquisitionDataSchema:
    session = mock_session()
    now = session.date
    now_local = now.astimezone()
    return ProtoAcquisitionDataSchema(
        data_stream_metadata=[
            _FipDataStreamMetadata(
                id=f"fip_{now_local.strftime('%Y-%m-%dT%H%M%S')}",
                start_time=now_local,
                end_time=now_local + datetime.timedelta(hours=1),
            )
        ],
        session=session,
        rig=mock_rig(),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate mock session and rig JSON files"
    )
    parser.add_argument(
        "--path-seed",
        default="./local/{schema}.json",
        help="Path template for output files (default: ./local/{schema}.json)",
    )
    args = parser.parse_args()

    example_session = mock_session()
    example_rig = mock_rig()
    example_mapped = make_mapped()

    os.makedirs(os.path.dirname(args.path_seed), exist_ok=True)

    for model in [example_session, example_rig, example_mapped]:
        with open(
            args.path_seed.format(schema=model.__class__.__name__),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(model.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
