# ForgeFlex X — Judge Q&A

## Why MILP?

MILP can represent both continuous decisions (grid power, battery power, SOC) and discrete decisions (when a flexible process starts). That matches the industrial scheduling problem.

## What is FlexDNA?

FlexDNA is our process-level flexibility representation: machine power, required duration, legal operating window, criticality and contiguous-operation requirement.

## Are machines physically switched?

Not in this prototype. ForgeFlex generates an optimal operating schedule. A real deployment could transfer the schedule to a factory EMS/PLC/VFD control layer.

## Why Simulink?

The optimizer is the decision engine. Simulink is a separate engineering twin used to validate the energy-flow behavior of the resulting setpoints.

## Why is the residual line flat?

It is a validation signal. The residual is the difference between energy supplied and energy consumed/charged/curtailed. A line near zero means the accounting closes.

## How is production protected?

Each flexible process must receive its exact required runtime inside its legal operating window. Fixed/critical demand remains represented as non-shiftable demand.

## What happens when constraints become impossible?

The optimization model is allowed to report infeasibility rather than fabricating a schedule. The dashboard should present this as a capacity/constraint diagnostic.

## Is the data from a real factory?

No. The current dataset is synthetic demonstration data. The architecture is designed so real SCADA/EMS/IoT data can replace the synthetic source.
