% 第五章示例代码：多普勒测速仿真
% 演示如何从多普勒频移计算目标速度

clear; close all; clc;
rng(0);

%% 参数设置
c = 3e8;              % 光速 (m/s)
f0 = 24e9;            % 雷达频率 24 GHz
v_target = 30;        % 目标速度 30 m/s (约108 km/h)
fs = 50e3;            % 采样率 50 kHz
T = 0.2;              % 观测时间 0.2 s

%% 计算理论多普勒频移
delta_f_theory = 2 * v_target * f0 / c;
fprintf('=== 多普勒测速仿真 ===\n');
fprintf('雷达频率: %.1f GHz\n', f0/1e9);
fprintf('目标速度: %.1f m/s (%.1f km/h)\n', v_target, v_target*3.6);
fprintf('理论多普勒频移: %.2f Hz\n\n', delta_f_theory);

%% 生成信号
t = 0:1/fs:T-1/fs;    % 时间轴

% 发射信号（复基带表示，实际载频为 f0）
tx_signal = ones(size(t));

% 回波信号（带多普勒频移），保留频率正负号信息
rx_signal = exp(1j * 2*pi*delta_f_theory*t);

% 添加噪声（模拟真实环境）
SNR_dB = 20;          % 信噪比 20 dB
noise = (randn(size(rx_signal)) + 1j * randn(size(rx_signal))) / sqrt(2);
noise = noise / sqrt(mean(abs(noise).^2)) * 10^(-SNR_dB/20);
rx_signal_noisy = rx_signal + noise;

%% 混频
% 将接收信号与发射信号混频，得到差频信号
mixed_signal = tx_signal .* rx_signal_noisy;

% 低通滤波（简化：直接使用混频结果）
% 实际系统中需要低通滤波器滤除高频分量

%% FFT频谱分析
N = length(mixed_signal);
freq = (-N/2:N/2-1) * (fs/N);
spectrum = fftshift(fft(mixed_signal));
spectrum_mag = abs(spectrum) / N;

% 找到峰值频率
[~, idx_max] = max(spectrum_mag);
delta_f_measured = freq(idx_max);

% 计算测量速度
v_measured = c * delta_f_measured / (2 * f0);

fprintf('=== 测量结果 ===\n');
fprintf('测量多普勒频移: %.2f Hz\n', delta_f_measured);
fprintf('测量速度: %.2f m/s (%.2f km/h)\n', v_measured, v_measured*3.6);
fprintf('测量误差: %.2f m/s (%.1f%%)\n\n', abs(v_measured - v_target), ...
        abs(v_measured - v_target)/v_target*100);

%% 绘图
figure('Position', [100, 100, 1200, 800]);

% 子图1: 时域信号
subplot(3,1,1);
plot(t(1:500)*1000, real(rx_signal(1:500)), 'b-', 'LineWidth', 1.5);
hold on;
plot(t(1:500)*1000, real(rx_signal_noisy(1:500)), 'r-', 'LineWidth', 0.8);
xlabel('时间 (ms)');
ylabel('幅度');
title('回波信号（时域）');
legend('无噪声', '含噪声');
grid on;

% 子图2: 混频后的差频信号
subplot(3,1,2);
plot(t(1:500)*1000, real(mixed_signal(1:500)), 'g-', 'LineWidth', 1);
xlabel('时间 (ms)');
ylabel('幅度');
title(sprintf('混频后的差频信号（实部，频率 ≈ %.0f Hz）', delta_f_theory));
grid on;

% 子图3: FFT频谱
subplot(3,1,3);
plot(freq, spectrum_mag, 'b-', 'LineWidth', 1.5);
hold on;
plot(delta_f_measured, spectrum_mag(idx_max), 'ro', 'MarkerSize', 10, ...
     'MarkerFaceColor', 'r');
xlabel('频率 (Hz)');
ylabel('幅度');
title(sprintf('FFT频谱（峰值频率 = %.2f Hz）', delta_f_measured));
legend('频谱', '峰值');
grid on;
xlim([-10000, 10000]);

%% 速度分辨率分析
delta_v = c / (2 * f0 * T);
fprintf('=== 性能分析 ===\n');
fprintf('速度分辨率: %.3f m/s (%.2f km/h)\n', delta_v, delta_v*3.6);
fprintf('观测时间: %.2f s\n', T);
fprintf('采样率: %.1f kHz\n', fs/1e3);

% 最大可测速度
v_max = c * fs / (4 * f0);
fprintf('最大可测速度: %.1f m/s (%.1f km/h)\n\n', v_max, v_max*3.6);

%% 多目标场景仿真
fprintf('=== 多目标场景 ===\n');
velocities = [20, 35, -15];  % 三个目标的速度 (m/s)
amplitudes = [1.0, 0.7, 0.5]; % 三个目标的回波强度

% 生成多目标回波
rx_multi = zeros(size(t));
for i = 1:length(velocities)
    delta_f_i = 2 * velocities(i) * f0 / c;
    rx_multi = rx_multi + amplitudes(i) * exp(1j * 2*pi*delta_f_i*t);
    fprintf('目标%d: 速度 = %.1f m/s, 频移 = %.1f Hz\n', ...
            i, velocities(i), delta_f_i);
end

% 添加噪声
noise_multi = (randn(size(rx_multi)) + 1j * randn(size(rx_multi))) / sqrt(2);
noise_multi = noise_multi / sqrt(mean(abs(noise_multi).^2)) * 10^(-SNR_dB/20);
rx_multi_noisy = rx_multi + noise_multi;

% 混频和FFT
mixed_multi = tx_signal .* rx_multi_noisy;
spectrum_multi = fftshift(fft(mixed_multi));
spectrum_multi_mag = abs(spectrum_multi) / N;

% 绘制多目标频谱
figure('Position', [150, 150, 1000, 500]);
plot(freq, spectrum_multi_mag, 'b-', 'LineWidth', 1.5);
hold on;

% 标注每个目标的理论频率
delta_f_targets = 2 * velocities * f0 / c;
y_limits = ylim;
y_text_levels = linspace(y_limits(2) * 0.72, y_limits(2) * 0.9, length(velocities));
for i = 1:length(velocities)
    delta_f_i = delta_f_targets(i);
    xline(delta_f_i, 'r--', 'LineWidth', 1.5);
    text(delta_f_i, y_text_levels(i), sprintf('目标%d', i), ...
         'Color', 'r', 'FontSize', 10, 'HorizontalAlignment', 'center', ...
         'VerticalAlignment', 'bottom', 'BackgroundColor', 'w', 'Margin', 1);
end

xlabel('频率 (Hz)');
ylabel('幅度');
title('多目标场景的多普勒频谱');
grid on;
x_limit = max(abs(delta_f_targets)) + 1000;
xlim([-x_limit, x_limit]);
legend('频谱', 'Location', 'best');

fprintf('\n仿真完成！\n');
