# MATLAB / Simulink layer

Build the engineering validation model here after the Python MVP works.

Suggested subsystems:
- `PV_Subsystem`
- `Grid_Subsystem`
- `BESS_Subsystem`
- `Critical_Loads`
- `Flexible_Loads`
- `Thermal_Storage`
- `Compressed_Air`
- `Production_Process`
- `ForgeFlex_Controller`
- `Data_Logger`

The Python optimizer should output a 24-hour setpoint schedule. Import that schedule into Simulink and verify energy balance, SOC bounds, production constraints and peak demand.
