import asyncio
import dataclasses
import logging
from pathlib import Path

import clabe.xml_rpc
from aind_behavior_services.session import AindBehaviorSessionModel
from clabe import resource_monitor
from clabe.apps import AindBehaviorServicesBonsaiApp, BonsaiApp
from clabe.data_transfer import robocopy
from clabe.launcher import Launcher, experiment
from clabe.pickers import DefaultBehaviorPicker, DefaultBehaviorPickerSettings

from aind_behavior_just_frames.rig import AindJustFramesRig, SatelliteRig
from aind_physiology_fip.rig import AindPhysioFipRig

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


@experiment(name="just_frames_with_satellites")
async def my_experiment(launcher: Launcher) -> None:
    # Get configuration from pickers
    picker_just_frames = DefaultBehaviorPicker(
        launcher=launcher,
        settings=DefaultBehaviorPickerSettings(
            config_library_dir=r"\\allen\aind\scratch\AindBehavior.db\AindBehaviorJustFrames"
        ),
    )

    picker_fip = DefaultBehaviorPicker(
        launcher=launcher,
        settings=DefaultBehaviorPickerSettings(
            config_library_dir=r"\\allen\aind\scratch\AindBehavior.db\AindPhysiologyFip"
        ),
    )
    session = picker_just_frames.pick_session(AindBehaviorSessionModel)

    rig_just_frames = picker_just_frames.pick_rig(AindJustFramesRig)
    rig_fip = picker_fip.pick_rig(AindPhysioFipRig)

    launcher.register_session(session, rig_just_frames.data_directory)

    # Validate resources
    resource_monitor.ResourceMonitor(
        constrains=[
            resource_monitor.available_storage_constraint_factory(
                launcher.data_directory, 2e11
            ),
        ]
    ).run()

    # Start assemblying rig communication
    has_satellites = len(rig_just_frames.satellite_rigs) > 0
    satellites: dict[str, SatelliteRigConnection] = {}
    if has_satellites:
        SATELLITE_UPLOAD_ROOT = "."
        for s in rig_just_frames.satellite_rigs:
            xml_client = clabe.xml_rpc.XmlRpcClient(
                settings=clabe.xml_rpc.XmlRpcClientSettings(
                    server_url=f"http://{s.zmq_protocol_config.address}:8000",
                    token="42",
                )
            )
            this_session = xml_client.upload_model(
                session, f"{SATELLITE_UPLOAD_ROOT}/{session.session_name}_session.json"
            )
            this_rig = xml_client.upload_model(
                s, f"{SATELLITE_UPLOAD_ROOT}/{session.session_name}_rig.json"
            )

            assert this_session.success, "Failed to upload session to satellite rig."
            assert this_rig.success, "Failed to upload rig to satellite rig."

            additional_externalized_properties = {
                "RigPath": this_rig.path,
                "SessionPath": this_session.path,
            }
            satellite_bonsai_app = BonsaiApp(
                workflow=Path(r"./Aind.Behavior.JustFrames/src/main.bonsai"),
                executable=Path(r"./Aind.Behavior.JustFrames/bonsai/bonsai.exe"),
                additional_externalized_properties=additional_externalized_properties,
            )
            satellites[s.rig_name] = SatelliteRigConnection(
                rig=s,
                xml_rpc_client=xml_client,
                bonsai_app=satellite_bonsai_app,
                xml_rpc_executor=clabe.xml_rpc.XmlRpcExecutor(client=xml_client),
            )

    # construct bonsai apps
    just_frames_bonsai_app = AindBehaviorServicesBonsaiApp(
        workflow=Path(r"./Aind.Behavior.JustFrames/src/main.bonsai"),
        executable=Path(r"./Aind.Behavior.JustFrames/bonsai/bonsai.exe"),
        rig=rig_just_frames,
        session=session,
    )

    fip_bonsai_app = AindBehaviorServicesBonsaiApp(
        workflow=Path(r"./Aind.Physiology.Fip/src/main.bonsai"),
        executable=Path(r"./Aind.Physiology.Fip/bonsai/bonsai.exe"),
        rig=rig_fip,
        session=session,
    )

    tasks = {
        satellite.rig.rig_name: satellite.xml_rpc_executor.run_async(
            satellite.bonsai_app.command
        )
        for satellite in satellites.values()
    }
    tasks[rig_just_frames.rig_name] = just_frames_bonsai_app.run_async()
    tasks["fip_task"] = fip_bonsai_app.run_async()

    results = await asyncio.gather(*tasks.values())

    for rig_id, result in dict(zip(tasks.keys(), results)).items():
        if result.exit_code != 0:
            logger.error(
                "RigId %s 's, App exited with error code %d. With stdout %s and stderr %s",
                rig_id,
                result.exit_code,
                result.stdout,
                result.stderr,
            )
        else:
            logger.info(
                "RigId %s 's, App completed successfully with stdout %s",
                rig_id,
                result.stdout,
            )
            logger.debug(
                "RigId %s 's, App completed successfully with stderr %s",
                rig_id,
                result.stderr,
            )

    # Copy data to central storage
    launcher.copy_logs()
    settings = robocopy.RobocopySettings()
    assert launcher.session.session_name is not None, "Session name is None"
    settings.destination = (
        Path(settings.destination)
        / launcher.session.subject
        / launcher.session.session_name
    )
    robocopy_tasks = {
        satellite.rig.rig_name: satellite.xml_rpc_executor.run_async(
            _make_robocopy_from_satellite_rig(
                settings, satellite.rig, launcher.session.session_name
            ).command
        )
        for satellite in satellites.values()
    }
    robocopy_tasks[rig_just_frames.rig_name] = robocopy.RobocopyService(
        source=rig_just_frames.data_directory / launcher.session.session_name,
        settings=settings,
    ).run_async()
    await asyncio.gather(*robocopy_tasks.values())
    return


@dataclasses.dataclass
class SatelliteRigConnection:
    rig: SatelliteRig
    xml_rpc_client: clabe.xml_rpc.XmlRpcClient
    xml_rpc_executor: clabe.xml_rpc.XmlRpcExecutor
    bonsai_app: BonsaiApp


def _make_robocopy_from_satellite_rig(
    robocopy_settings: robocopy.RobocopySettings, rig: SatelliteRig, session_name: str
) -> robocopy.RobocopyService:
    # For videos, we flatten everything in the behavior-videos directory
    # Everything else gets dumped in the behavior directory under .satellites/rig_name/
    source = {
        rig.data_directory / session_name / "behavior-videos": Path(
            robocopy_settings.destination
        )
        / "behavior-videos",
        rig.data_directory / session_name / "behavior": Path(
            robocopy_settings.destination
        )
        / "behavior"
        / "satellites"
        / rig.rig_name,
    }
    settings = robocopy_settings.model_copy(
        update={"destination": None}
    )  # we will set destination per-path
    return robocopy.RobocopyService(source=source, settings=settings)


if __name__ == "__main__":
    from clabe.launcher import LauncherCliArgs

    launcher = Launcher(settings=LauncherCliArgs())
    launcher.run_experiment(my_experiment)
