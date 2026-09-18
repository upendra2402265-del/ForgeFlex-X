%% FORGEFLEX X — REVIEW 2 SIMPLE SHOWCASE V2
% ============================================================
% PURPOSE
% A very simple, reliable jury-demo controller.
%
% Instead of showing four panels at once, this version uses
% one strong ENERGY FLOW graph and one BATTERY/PRODUCTION graph.
% This avoids blank subplot problems in MATLAB Online.
%
% It varies the operating condition and shows the result:
%   0 = Automatic 5-scenario demo
%   1 = Normal Day
%   2 = Cloudy Day
%   3 = High Solar
%   4 = High Production
%   5 = Low Battery
%
% The Simulink model is also updated and run when available.
% The plotted curves are the scenario operating trajectories.
%
% ============================================================

clc;

MODEL = 'ForgeFlex_X_Review2_DemoTwin';
MATNAME = 'review2_simulink_inputs.mat';

fprintf('\n============================================================\n');
fprintf(' FORGEFLEX X — REVIEW 2 SIMPLE SHOWCASE V2\n');
fprintf('============================================================\n\n');

%% 1. Find MAT file

matPath = findFile(pwd,MATNAME);

if isempty(matPath)
    error(['Cannot find ' MATNAME '. ' ...
        'Keep this script in the same MATLAB Drive folder as the MAT file.']);
end

D = load(matPath);

if ~isfield(D,'time_h') || ...
   ~isfield(D,'pv_kw') || ...
   ~isfield(D,'fixed_load_kw') || ...
   ~isfield(D,'flex_load_kw') || ...
   ~isfield(D,'charge_kw') || ...
   ~isfield(D,'discharge_kw')

    error('The MAT file does not contain the expected Review 2 signals.');
end

t = double(D.time_h(:));

pvBase      = getValues(D.pv_kw,t);
fixedBase   = getValues(D.fixed_load_kw,t);
flexBase    = getValues(D.flex_load_kw,t);
chargeBase  = getValues(D.charge_kw,t);
dischBase   = getValues(D.discharge_kw,t);

fprintf('Loaded %d hourly points.\n',numel(t));

%% 2. Select scenario

fprintf('\nChoose the demonstration:\n');
fprintf('  0  Automatic 5-scenario demo\n');
fprintf('  1  Normal Day\n');
fprintf('  2  Cloudy Day\n');
fprintf('  3  High Solar\n');
fprintf('  4  High Production\n');
fprintf('  5  Low Battery\n\n');

choice = input('Enter 0-5: ');

if isempty(choice) || ~isscalar(choice) || ~ismember(choice,0:5)
    error('Enter only one number from 0 to 5.');
end

%% 3. Open Simulink model if available

modelAvailable = false;

if bdIsLoaded(MODEL)
    modelAvailable = true;
else
    modelPath = findFile(pwd,[MODEL '.slx']);
    if ~isempty(modelPath)
        load_system(modelPath);
        modelAvailable = true;
    end
end

%% 4. Decide scenarios

if choice == 0
    ids = 1:5;
else
    ids = choice;
end

%% 5. Two reusable figures

figPower = figure( ...
    'Name','ForgeFlex X — Energy Flow Showcase', ...
    'NumberTitle','off', ...
    'Color','white', ...
    'Position',[100 120 1100 600]);

figState = figure( ...
    'Name','ForgeFlex X — Battery + Production Showcase', ...
    'NumberTitle','off', ...
    'Color','white', ...
    'Position',[140 160 1100 600]);

%% 6. Run scenarios

for z = 1:numel(ids)

    id = ids(z);

    [pv,fixed,flex,charge,discharge] = ...
        makeScenario(id,pvBase,fixedBase,flexBase,chargeBase,dischBase);

    [charge,discharge,soc,grid,curtail] = ...
        physicalScenario(pv,fixed,flex,charge,discharge);

    % Send scenario into Simulink base workspace.
    assignin('base','forgeflex_pv_demo',[t pv]);
    assignin('base','forgeflex_grid_demo',[t grid]);
    assignin('base','forgeflex_discharge_demo',[t discharge]);
    assignin('base','forgeflex_fixed_demo',[t fixed]);
    assignin('base','forgeflex_flex_demo',[t flex]);
    assignin('base','forgeflex_charge_demo',[t charge]);
    assignin('base','forgeflex_curtail_demo',[t curtail]);

    %% Run same Simulink model, if it exists.

    if modelAvailable
        try
            set_param(MODEL,'SimulationCommand','update');
            sim(MODEL);
            fprintf('Simulink: PASS — %s\n',scenarioName(id));
        catch ME
            fprintf('Simulink: skipped safely (%s)\n',ME.message);
        end
    end

    %% Metrics

    residual = pv + grid + discharge ...
             - fixed - flex - charge - curtail;

    peakGrid = max(grid);
    peakFactory = max(fixed+flex);
    renewable = sum(pv);
    utilized = min(renewable,sum(fixed+flex)+sum(charge));

    if renewable > 0
        renewablePct = 100*utilized/renewable;
    else
        renewablePct = 0;
    end

    %% --------------------------------------------------------
    % FIGURE 1: MAIN ENERGY FLOW GRAPH
    % ---------------------------------------------------------

    figure(figPower);
    clf(figPower);

    plot(t,pv,'LineWidth',2.8);
    hold on;

    plot(t,grid,'LineWidth',2.5);
    plot(t,fixed+flex,'LineWidth',2.5);
    plot(t,discharge,'--','LineWidth',2.0);
    plot(t,charge,'--','LineWidth',2.0);

    grid on;
    xlim([0 23]);

    xlabel('Time (hour)','FontWeight','bold');
    ylabel('Power (kW)','FontWeight','bold');

    title(['FORGEFLEX X — ENERGY FLOW | ' ...
        upper(scenarioName(id))], ...
        'FontSize',16,'FontWeight','bold');

    legend( ...
        {'☀ PV Generation', ...
         '⚡ Grid Import', ...
         '🏭 Factory Demand', ...
         '🔋 Battery Discharge', ...
         '🔋 Battery Charge'}, ...
        'Location','best');

    info = sprintf( ...
        'Peak Grid = %.1f kW   |   Peak Factory = %.1f kW   |   Renewable Utilization = %.1f%%', ...
        peakGrid,peakFactory,renewablePct);

    subtitle(info);

    %% --------------------------------------------------------
    % FIGURE 2: BATTERY + PRODUCTION
    % ---------------------------------------------------------

    figure(figState);
    clf(figState);

    ax1 = axes('Position',[0.09 0.56 0.85 0.34]);

    plot(ax1,t,soc,'LineWidth',2.8);
    hold(ax1,'on');
    plot(ax1,[0 23],[100 100],'--','LineWidth',1.2);
    plot(ax1,[0 23],[475 475],'--','LineWidth',1.2);

    grid(ax1,'on');
    xlim(ax1,[0 23]);
    ylim(ax1,[70 500]);

    xlabel(ax1,'Time (hour)');
    ylabel(ax1,'Battery Energy (kWh)');

    title(ax1,'BATTERY STATE OF CHARGE','FontWeight','bold');

    legend(ax1,{'SOC','Minimum = 100 kWh','Maximum = 475 kWh'}, ...
        'Location','best');

    ax2 = axes('Position',[0.09 0.09 0.85 0.34]);

    plot(ax2,t,fixed,'LineWidth',2.5);
    hold(ax2,'on');
    plot(ax2,t,flex,'LineWidth',2.5);

    grid(ax2,'on');
    xlim(ax2,[0 23]);

    xlabel(ax2,'Time (hour)');
    ylabel(ax2,'Power (kW)');

    title(ax2,'PRODUCTION LOAD: FIXED vs FLEXIBLE','FontWeight','bold');

    legend(ax2,{'Fixed / Critical Load','Flexible Industrial Load'}, ...
        'Location','best');

    %% Main window title

    try
        sgtitle(figState, ...
            ['FORGEFLEX X — STATE VIEW | ' scenarioName(id)], ...
            'FontSize',16,'FontWeight','bold');
    catch
        % MATLAB versions without sgtitle still work.
    end

    drawnow;

    fprintf('\nScenario: %s\n',scenarioName(id));
    fprintf('  Peak grid          : %.2f kW\n',peakGrid);
    fprintf('  Peak factory       : %.2f kW\n',peakFactory);
    fprintf('  Renewable use      : %.1f %%\n',renewablePct);
    fprintf('  Balance error      : %.9f kW\n',max(abs(residual)));
    fprintf('  Final battery SOC  : %.2f kWh\n',soc(end));

    fprintf('\nExplain to jury:\n');

    switch id
        case 1
            fprintf('Normal operating condition.\n');
        case 2
            fprintf('Cloudy day: renewable generation drops; grid/storage support changes.\n');
        case 3
            fprintf('High solar: renewable contribution increases and grid requirement falls.\n');
        case 4
            fprintf('High production: factory demand increases.\n');
        case 5
            fprintf('Low battery: storage support is reduced, so grid support increases.\n');
    end

    if choice == 0 && z < numel(ids)
        fprintf('\nNext scenario in 3 seconds...\n');
        pause(3);
    end
end

fprintf('\n============================================================\n');
fprintf(' REVIEW 2 SHOWCASE COMPLETE\n');
fprintf('============================================================\n');
fprintf('Use the Energy Flow window as the MAIN jury screen.\n');
fprintf('Use Battery + Production as the supporting screen.\n');
fprintf('Use Simulink Energy Balance Scope as the proof/validation screen.\n');
fprintf('============================================================\n');


%% ============================================================
% LOCAL FUNCTIONS
% ============================================================

function pathOut = findFile(root,name)

    pathOut = '';

    direct = fullfile(root,name);

    if isfile(direct)
        pathOut = direct;
        return;
    end

    hit = dir(fullfile(root,'**',name));

    if ~isempty(hit)
        pathOut = fullfile(hit(1).folder,hit(1).name);
    end
end


function v = getValues(raw,t)

    x = double(raw);

    if isvector(x)

        x = x(:);

        if numel(x) ~= numel(t)
            error('Signal length does not match time_h.');
        end

        v = x;
        return;
    end

    if size(x,1)==numel(t) && size(x,2)==2
        v = x(:,2);
        return;
    end

    if size(x,1)==2 && size(x,2)==numel(t)
        v = x(2,:).';
        return;
    end

    error('Unsupported signal dimensions.');
end


function name = scenarioName(id)

    names = { ...
        'Normal Day', ...
        'Cloudy Day', ...
        'High Solar', ...
        'High Production', ...
        'Low Battery'};

    name = names{id};
end


function [pv,fixed,flex,charge,discharge] = ...
    makeScenario(id,pv0,fixed0,flex0,charge0,disch0)

    pv = pv0;
    fixed = fixed0;
    flex = flex0;
    charge = charge0;
    discharge = disch0;

    switch id

        case 1
            % Normal.

        case 2
            % Cloudy.
            pv = 0.45*pv0;
            charge = 0.45*charge0;
            discharge = 1.10*disch0;

        case 3
            % High solar.
            pv = 1.35*pv0;
            charge = 1.30*charge0;
            discharge = 0.65*disch0;

        case 4
            % High production.
            fixed = 1.20*fixed0;
            flex = 1.20*flex0;

        case 5
            % Low battery support.
            charge = 0.50*charge0;
            discharge = zeros(size(disch0));

    end
end


function [charge,discharge,soc,grid,curtail] = ...
    physicalScenario(pv,fixed,flex,charge,discharge)

    n = numel(pv);

    EMIN = 100;
    EMAX = 475;
    SOC0 = 300;

    ETA_C = 0.95;
    ETA_D = 0.95;

    charge = max(0,charge);
    discharge = max(0,discharge);

    soc = zeros(n,1);
    grid = zeros(n,1);
    curtail = zeros(n,1);

    current = SOC0;

    for k=1:n

        maxDischarge = max(0,(current-EMIN)*ETA_D);

        discharge(k) = min(discharge(k),maxDischarge);

        maxCharge = max(0,(EMAX-current)/ETA_C);

        charge(k) = min(charge(k),maxCharge);

        demand = fixed(k)+flex(k)+charge(k);
        available = pv(k)+discharge(k);

        if available >= demand
            grid(k)=0;
            curtail(k)=available-demand;
        else
            grid(k)=demand-available;
            curtail(k)=0;
        end

        current = current ...
            + ETA_C*charge(k) ...
            - discharge(k)/ETA_D;

        current = min(EMAX,max(EMIN,current));

        soc(k)=current;

    end
end
