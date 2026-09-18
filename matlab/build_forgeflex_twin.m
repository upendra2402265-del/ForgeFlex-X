function modelName = build_forgeflex_twin()
% Build a simple ForgeFlex X engineering twin from Python-generated inputs.
% This script uses only standard Simulink blocks.
%
% Before running:
%   1) Run: python scripts/run_review2.py
%   2) In MATLAB, cd to the ForgeFlex project root.
%   3) Run: modelName = build_forgeflex_twin;
%
% The model validates the Python/MILP schedule using:
%   PV + Grid + Battery_Discharge - Curtailment
%       = Fixed_Load + Flexible_Load + Battery_Charge
%
% and computes battery SOC from charge/discharge commands.

modelName = 'ForgeFlex_X_Review2_Twin';
root = fileparts(mfilename('fullpath'));
matFile = fullfile(root, '..', 'review2_outputs', 'review2_simulink_inputs.mat');
matFile = char(java.io.File(matFile).getCanonicalPath());

if ~isfile(matFile)
    error('Missing %s. Run scripts/run_review2.py first.', matFile);
end

S = load(matFile);
req = {'time_h','pv_kw','fixed_load_kw','flex_load_kw','grid_kw','charge_kw','discharge_kw','curtail_kw'};
for k = 1:numel(req)
    if ~isfield(S, req{k})
        error('MAT input is missing variable %s.', req{k});
    end
end

% Convert [time value] arrays into timetable-like From Workspace data.
pv_data     = S.pv_kw;
fixed_data  = S.fixed_load_kw;
flex_data   = S.flex_load_kw;
grid_data   = S.grid_kw;
charge_data = S.charge_kw;
discharge_data = S.discharge_kw;
curtail_data = S.curtail_kw;

% Start clean.
if bdIsLoaded(modelName)
    close_system(modelName, 0);
end
if exist([modelName '.slx'], 'file')
    delete([modelName '.slx']);
end

new_system(modelName);
open_system(modelName);
set_param(modelName, 'Solver', 'FixedStepDiscrete', 'FixedStep', '1', 'StopTime', '23');

% -------------------- SOURCE BLOCKS --------------------
blocks = {
    'pv_kw',       'PV / Renewable',       [40 40 180 75],   pv_data;
    'fixed_load_kw','Fixed / Critical Load',[40 120 180 155], fixed_data;
    'flex_load_kw','Flexible Process Load',[40 200 180 235], flex_data;
    'grid_kw',     'Grid Setpoint',        [40 280 180 315], grid_data;
    'charge_kw',   'Battery Charge',       [40 360 180 395], charge_data;
    'discharge_kw','Battery Discharge',    [40 440 180 475], discharge_data;
    'curtail_kw',  'PV Curtailment',       [40 520 180 555], curtail_data;
};

for i = 1:size(blocks,1)
    add_block('simulink/Sources/From Workspace', [modelName '/' blocks{i,2}], ...
        'Position', blocks{i,3}, ...
        'VariableName', blocks{i,1}, ...
        'Interpolate','off');
end

% -------------------- ENERGY BALANCE --------------------
add_block('simulink/Math Operations/Sum', [modelName '/Energy Balance'], ...
    'Position',[300 210 335 430], ...
    'Inputs','++- --');

% A single Sum block is used for the residual. Inputs are arranged as:
% +grid +discharge +PV -curtail -charge -fixed -flex.
% The order is set by explicit lines below; an easier robust route is eight-input Sum.
set_param([modelName '/Energy Balance'],'Inputs','++++++++');

% Residual = grid + discharge + pv - curtail - charge - fixed - flex.
% We therefore use a Gain(-1) on negative contributors.
negNames = {'Curtail Neg','Charge Neg','Fixed Neg','Flex Neg'};
negSrc   = {[modelName '/PV Curtailment'], [modelName '/Battery Charge'], [modelName '/Fixed / Critical Load'], [modelName '/Flexible Process Load']};
negVars  = {'1','1','1','1'};
for i = 1:numel(negNames)
    add_block('simulink/Math Operations/Gain', [modelName '/' negNames{i}], ...
        'Position',[230 510+(i-1)*75 270 545+(i-1)*75], 'Gain','-1');
end

% Sum positive sources using a second Sum block.
add_block('simulink/Math Operations/Sum',[modelName '/Positive Sources'], ...
    'Position',[300 40 335 140],'Inputs','+++');
add_block('simulink/Math Operations/Sum',[modelName '/Negative Loads'], ...
    'Position',[300 500 335 680],'Inputs','++++');
add_block('simulink/Math Operations/Sum',[modelName '/Residual'], ...
    'Position',[410 260 450 330],'Inputs','+-');

% -------------------- BATTERY SOC --------------------
add_block('simulink/Math Operations/Gain',[modelName '/Charge Efficiency'], ...
    'Position',[270 720 315 755],'Gain','0.95');
add_block('simulink/Math Operations/Gain',[modelName '/Discharge Efficiency'], ...
    'Position',[270 800 315 835],'Gain',num2str(1/0.95));
add_block('simulink/Math Operations/Sum',[modelName '/Battery Net Power'], ...
    'Position',[410 730 450 815],'Inputs','+-');
add_block('simulink/Discrete/Discrete-Time Integrator',[modelName '/SOC Integrator'], ...
    'Position',[510 735 590 805], ...
    'InitialCondition','300', ...
    'SampleTime','1');
add_block('simulink/Discontinuities/Saturation',[modelName '/SOC Limits'], ...
    'Position',[650 735 715 805], ...
    'UpperLimit','475', 'LowerLimit','100');

% -------------------- DISPLAYS / LOGGING --------------------
add_block('simulink/Sinks/Scope',[modelName '/Energy Balance Scope'], ...
    'Position',[520 250 700 340]);
add_block('simulink/Sinks/Scope',[modelName '/SOC Scope'], ...
    'Position',[760 710 940 810]);
add_block('simulink/Sinks/To Workspace',[modelName '/Residual To Workspace'], ...
    'Position',[520 350 660 385], ...
    'VariableName','forgeflex_residual', ...
    'SaveFormat','Array');
add_block('simulink/Sinks/To Workspace',[modelName '/SOC To Workspace'], ...
    'Position',[760 830 900 865], ...
    'VariableName','forgeflex_soc', ...
    'SaveFormat','Array');

% -------------------- CONNECTIONS --------------------
% Sources: PV, Grid, Discharge are positive.
add_line(modelName,'Grid Setpoint/1','Positive Sources/1','autorouting','on');
add_line(modelName,'Battery Discharge/1','Positive Sources/2','autorouting','on');
add_line(modelName,'PV / Renewable/1','Positive Sources/3','autorouting','on');

% Negative: Curtail, Charge, Fixed, Flex.
add_line(modelName,'PV Curtailment/1','Curtail Neg/1','autorouting','on');
add_line(modelName,'Battery Charge/1','Charge Neg/1','autorouting','on');
add_line(modelName,'Fixed / Critical Load/1','Fixed Neg/1','autorouting','on');
add_line(modelName,'Flexible Process Load/1','Flex Neg/1','autorouting','on');
add_line(modelName,'Curtail Neg/1','Negative Loads/1','autorouting','on');
add_line(modelName,'Charge Neg/1','Negative Loads/2','autorouting','on');
add_line(modelName,'Fixed Neg/1','Negative Loads/3','autorouting','on');
add_line(modelName,'Flex Neg/1','Negative Loads/4','autorouting','on');
add_line(modelName,'Positive Sources/1','Residual/1','autorouting','on');
add_line(modelName,'Negative Loads/1','Residual/2','autorouting','on');

% SOC path.
add_line(modelName,'Battery Charge/1','Charge Efficiency/1','autorouting','on');
add_line(modelName,'Battery Discharge/1','Discharge Efficiency/1','autorouting','on');
add_line(modelName,'Charge Efficiency/1','Battery Net Power/1','autorouting','on');
add_line(modelName,'Discharge Efficiency/1','Battery Net Power/2','autorouting','on');
add_line(modelName,'Battery Net Power/1','SOC Integrator/1','autorouting','on');
add_line(modelName,'SOC Integrator/1','SOC Limits/1','autorouting','on');

% Scopes/logs.
add_line(modelName,'Residual/1','Energy Balance Scope/1','autorouting','on');
add_line(modelName,'Residual/1','Residual To Workspace/1','autorouting','on');
add_line(modelName,'SOC Limits/1','SOC Scope/1','autorouting','on');
add_line(modelName,'SOC Limits/1','SOC To Workspace/1','autorouting','on');

% Add annotations.
add_block('simulink/Signal Routing/From Workspace',[modelName '/README Marker'], ...
    'Position',[940 70 1090 105], 'VariableName','time_h');

set_param(modelName,'ZoomFactor','FitSystem');
save_system(modelName,[modelName '.slx']);

fprintf('\nForgeFlex X Simulink twin created: %s.slx\n',modelName);
fprintf('Run the model and inspect:\n');
fprintf('  Energy Balance Scope\n');
fprintf('  SOC Scope\n');
fprintf('  forgeflex_residual\n');
fprintf('  forgeflex_soc\n');

end
