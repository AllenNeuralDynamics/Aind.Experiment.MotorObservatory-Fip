# AIND Experiment: MotorObservatory + FIP

An repository for an experiment that acquires data from MotorObservatory and FIP.

## Getting started

1. Ensure the requirements of both repositories [Aind.Behavior.JustFrames](https://github.com/AllenNeuralDynamics/Aind.Behavior.JustFrames)and [Aind.Physiology.Fip](https://github.com/AllenNeuralDynamics/Aind.Physiology.Fip/) are fulfilled. This repository requires uv to be installed!
2. Clone this repository
3. Run `./scripts/deploy.cmd`
4. (Optional) If you need an additional computer to run camera acquisition, run `scripts/serve.cmd` on that computer after ensuring the requirements are fulfilled there as well.
5. `main.py` provides an easy way to launch the combined experiment. Feel free to locally change the `experiment` function to whatever fits your need.
6. Run the experiment by `uv run clabe run main.py` (or target whatever specific script you want to run).
