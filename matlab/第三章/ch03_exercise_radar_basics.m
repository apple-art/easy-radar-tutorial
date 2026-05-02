%% ch03_exercise_radar_basics.m
% 第三章练习：雷达信号基础
% 对应章节：3.1 脉冲参数 / 3.3 距离衰减 / 3.4 多普勒效应
%
% 运行方式：在 MATLAB 中逐节运行（Ctrl+Enter），观察输出和图形

%% ========================================================
%  练习 1：脉冲参数计算
%  对应 3.1 节
% =========================================================

c = 3e8;  % 光速 (m/s)

% 已知参数
tau = 1e-6;       % 脉冲宽度 1 μs
PRI = 1.5e-3;     % 脉冲重复间隔 1.5 ms

% (a) 最大不模糊距离
R_max = c * PRI / 2;
fprintf('最大不模糊距离 R_max = %.0f km\n', R_max/1e3);

% (b) 占空比
duty_cycle = tau / PRI;
fprintf('占空比 = %.4f (%.2f%%)\n', duty_cycle, duty_cycle*100);

% (c) 若平均功率为 1 kW，峰值功率是多少？
P_avg = 1e3;  % 1 kW
P_peak = P_avg / duty_cycle;
fprintf('峰值功率 P_peak = %.2f MW\n', P_peak/1e6);

% 思考：为什么脉冲雷达需要如此高的峰值功率？
% 答：占空比极低（<0.1%），要在极短时间内打出足够能量，
%     峰值功率必须远高于平均功率。

%% ========================================================
%  练习 2：距离衰减——1/R^4 的量级感
%  对应 3.3 节
% =========================================================

R_ref = 50e3;   % 参考距离 50 km
R_test = [100, 200, 400] * 1e3;  % 测试距离 (m)

fprintf('\n--- 距离衰减 ---\n');
fprintf('参考距离：%.0f km\n', R_ref/1e3);
for i = 1:length(R_test)
    ratio = (R_ref / R_test(i))^4;
    loss_dB = 10 * log10(ratio);
    fprintf('距离 %.0f km：功率变为参考的 1/%.0f (%.1f dB)\n', ...
        R_test(i)/1e3, 1/ratio, loss_dB);
end

% 绘制 1/R^4 衰减曲线
R_plot = linspace(10, 500, 500) * 1e3;  % 10~500 km
P_norm = (R_ref ./ R_plot).^4;          % 归一化到 R_ref 处

figure('Name', '距离衰减曲线');
semilogy(R_plot/1e3, P_norm, 'b-', 'LineWidth', 2);
hold on;
semilogy(R_plot/1e3, (R_ref./R_plot).^2, 'g--', 'LineWidth', 1.5);
xlabel('距离 R (km)');
ylabel('归一化接收功率');
title('1/R^4 vs 1/R^2 衰减对比');
legend('1/R^4 (雷达回波)', '1/R^2 (声音/单程)');
grid on;

%% ========================================================
%  练习 3：雷达方程——接收功率估算
%  对应 3.3 节
% =========================================================

% 雷达参数（典型 S 波段搜索雷达）
Pt = 1e6;       % 发射峰值功率 1 MW
G  = 1000;      % 天线增益 30 dB
lambda = 0.1;   % 波长 0.1 m（3 GHz）
sigma = 10;     % 目标 RCS 10 m²（战斗机）

R_range = [50, 100, 200, 300] * 1e3;  % 目标距离

fprintf('\n--- 雷达方程：接收功率 ---\n');
fprintf('%-10s %-15s %-12s\n', '距离(km)', 'Pr (W)', 'Pr (dBW)');
for i = 1:length(R_range)
    Pr = Pt * G^2 * lambda^2 * sigma / ((4*pi)^3 * R_range(i)^4);
    fprintf('%-10.0f %-15.3e %-12.1f\n', R_range(i)/1e3, Pr, 10*log10(Pr));
end

% 思考：100 km 处的接收功率是皮瓦量级，而发射功率是兆瓦级，
%       这就是为什么雷达接收机需要极高增益放大器的原因。

%% ========================================================
%  练习 4：多普勒频移计算与频域检测
%  对应 3.4 节
% =========================================================

% 雷达参数
f0 = 3e9;           % 发射频率 3 GHz（S 波段）
lambda_s = c / f0;  % 波长

% 不同目标的径向速度
vr = [0, 50, 100, 300, -200];  % m/s（负号表示远离）
target_names = {'静止目标', '慢速车辆', '飞机', '战斗机', '远离目标'};

fprintf('\n--- 多普勒频移 ---\n');
fprintf('雷达频率：%.1f GHz，波长：%.2f m\n', f0/1e9, lambda_s);
fprintf('%-12s %-12s %-12s\n', '目标', '径向速度(m/s)', '多普勒频移(Hz)');
for i = 1:length(vr)
    fd = 2 * vr(i) / lambda_s;
    fprintf('%-12s %-12.0f %-12.1f\n', target_names{i}, vr(i), fd);
end

% 演示：时域 vs 频域检测多普勒频移
fs_demo = 1e6;      % 采样率 1 MHz
T_demo  = 0.1;      % 观测时长 0.1 s
t_demo  = 0:1/fs_demo:T_demo-1/fs_demo;

f_carrier = 10e3;   % 示意载波 10 kHz
fd_demo   = 300;    % 示意多普勒频移 300 Hz

tx_demo = sin(2*pi*f_carrier*t_demo);
rx_demo = 0.3 * sin(2*pi*(f_carrier + fd_demo)*t_demo);

% 频域分析
N = length(t_demo);
freq_axis = (0:N/2) * fs_demo / N;
TX_fft = fft(tx_demo);
RX_fft = fft(rx_demo);
TX_spec = 2 * abs(TX_fft(1:N/2+1)) / N;
RX_spec = 2 * abs(RX_fft(1:N/2+1)) / N;

% 只显示载波附近
f_low = 9000; f_high = 11500;
mask = (freq_axis >= f_low) & (freq_axis <= f_high);

figure('Name', '多普勒频移：时域 vs 频域');
subplot(1,2,1);
t_show = t_demo(t_demo < 0.002);
plot(t_show*1e3, tx_demo(t_demo < 0.002), 'b', 'LineWidth', 1); hold on;
plot(t_show*1e3, rx_demo(t_demo < 0.002), 'r--', 'LineWidth', 1);
xlabel('时间 (ms)'); ylabel('幅度');
title('时域：几乎无法区分');
legend('发射', '回波');

subplot(1,2,2);
plot(freq_axis(mask), TX_spec(mask), 'b', 'LineWidth', 1.5); hold on;
plot(freq_axis(mask), RX_spec(mask), 'r--', 'LineWidth', 1.5);
xlabel('频率 (Hz)'); ylabel('幅度谱');
title(sprintf('频域：清晰可见 %d Hz 偏移', fd_demo));
legend('发射', '回波');
grid on;



