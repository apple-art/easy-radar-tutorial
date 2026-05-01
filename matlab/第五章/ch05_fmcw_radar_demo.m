% 第五章高级示例：FMCW 雷达仿真（双斜坡简化版）
% 用上、下两个 chirp 同时恢复目标距离和速度

clear; close all; clc;
rng(0);

fprintf('=== FMCW雷达仿真（双斜坡简化版）===\n\n');

%% 参数设置
c = 3e8;              % 光速
f0 = 77e9;            % 载频 77 GHz
B = 150e6;            % 调频带宽 150 MHz
T_chirp = 1e-3;       % 单个 chirp 时间 1 ms
fs = 2e6;             % 采样率 2 MHz
slope = B / T_chirp;  % 调频斜率

% 目标参数
R_target = 50;        % 目标距离 50 m
v_target = 20;        % 目标速度 20 m/s (72 km/h)

fprintf('雷达参数：\n');
fprintf('  载频: %.0f GHz\n', f0 / 1e9);
fprintf('  调频带宽: %.0f MHz\n', B / 1e6);
fprintf('  Chirp时间: %.2f ms\n', T_chirp * 1e3);
fprintf('\n目标参数：\n');
fprintf('  距离: %.0f m\n', R_target);
fprintf('  速度: %.0f m/s (%.0f km/h)\n\n', v_target, v_target * 3.6);

%% 理论计算
tau = 2 * R_target / c;       % 时间延迟
f_d = 2 * v_target * f0 / c;  % 多普勒频移

% 对于 tx .* conj(rx) 的解调约定：
% 上扫频 beat = S*tau - f_d
% 下扫频 beat = S*tau + f_d
f_beat_up = slope * tau - f_d;
f_beat_down = slope * tau + f_d;

fprintf('理论值：\n');
fprintf('  时间延迟: %.2f ns\n', tau * 1e9);
fprintf('  多普勒频移: %.2f kHz\n', f_d / 1e3);
fprintf('  上扫频差频: %.2f kHz\n', f_beat_up / 1e3);
fprintf('  下扫频差频: %.2f kHz\n\n', f_beat_down / 1e3);

%% 信号生成
t = 0:1/fs:T_chirp-1/fs;  % 时间轴
valid = t >= tau;
t_delayed = zeros(size(t));
t_delayed(valid) = t(valid) - tau;

% 采用复基带 chirp，避免直接采样 77 GHz 载频
tx_up = exp(1j * pi * slope * t.^2);
tx_down = exp(-1j * pi * slope * t.^2);

rx_up = zeros(size(t));
rx_down = zeros(size(t));
rx_up(valid) = exp(1j * pi * slope * t_delayed(valid).^2) ...
             .* exp(1j * 2*pi * f_d * t(valid));
rx_down(valid) = exp(-1j * pi * slope * t_delayed(valid).^2) ...
               .* exp(1j * 2*pi * f_d * t(valid));

% 解调得到 beat 信号
beat_up = tx_up .* conj(rx_up);
beat_down = tx_down .* conj(rx_down);

% 添加噪声
SNR_dB = 15;
noise_up = (randn(size(beat_up)) + 1j * randn(size(beat_up))) / sqrt(2);
noise_up = noise_up / sqrt(mean(abs(noise_up).^2)) * 10^(-SNR_dB/20);
noise_down = (randn(size(beat_down)) + 1j * randn(size(beat_down))) / sqrt(2);
noise_down = noise_down / sqrt(mean(abs(noise_down).^2)) * 10^(-SNR_dB/20);
beat_up_noisy = beat_up + noise_up;
beat_down_noisy = beat_down + noise_down;

%% FFT 分析
N = length(t);
freq_signed = (-N/2:N/2-1) * (fs / N);
spectrum_up = fftshift(fft(beat_up_noisy));
spectrum_down = fftshift(fft(beat_down_noisy));
spectrum_up_mag = abs(spectrum_up) / N;
spectrum_down_mag = abs(spectrum_down) / N;

% 上扫频峰值应落在正频率一侧，下扫频峰值应落在负频率一侧
pos_mask = freq_signed >= 0;
neg_mask = freq_signed <= 0;

[~, idx_up_local] = max(spectrum_up_mag(pos_mask));
freq_pos = freq_signed(pos_mask);
spec_up_pos = spectrum_up_mag(pos_mask);
f_beat_up_measured = freq_pos(idx_up_local);

[~, idx_down_local] = max(spectrum_down_mag(neg_mask));
freq_neg = freq_signed(neg_mask);
spec_down_neg = spectrum_down_mag(neg_mask);
f_beat_down_signed = freq_neg(idx_down_local);
f_beat_down_measured = abs(f_beat_down_signed);

% 用上下扫频联合解耦距离与速度
range_freq_measured = (f_beat_up_measured + f_beat_down_measured) / 2;
f_d_measured = (f_beat_down_measured - f_beat_up_measured) / 2;
R_measured = c * range_freq_measured / (2 * slope);
v_measured = c * f_d_measured / (2 * f0);

fprintf('测量结果：\n');
fprintf('  上扫频差频: %.2f kHz\n', f_beat_up_measured / 1e3);
fprintf('  下扫频差频: %.2f kHz\n', f_beat_down_measured / 1e3);
fprintf('  恢复距离: %.2f m\n', R_measured);
fprintf('  恢复速度: %.2f m/s\n', v_measured);
fprintf('  距离误差: %.2f m\n', abs(R_measured - R_target));
fprintf('  速度误差: %.2f m/s\n\n', abs(v_measured - v_target));

%% 绘图
figure('Position', [100, 100, 1200, 900]);

% 子图1：上扫频瞬时频率
subplot(3,2,1);
tx_up_freq = slope * t;
plot(t * 1e3, tx_up_freq / 1e6, 'b-', 'LineWidth', 1.5);
xlabel('时间 (ms)');
ylabel('频率偏移 (MHz)');
title('上扫频发射信号（基带）');
grid on;

% 子图2：下扫频瞬时频率
subplot(3,2,2);
tx_down_freq = -slope * t;
plot(t * 1e3, tx_down_freq / 1e6, 'r-', 'LineWidth', 1.5);
xlabel('时间 (ms)');
ylabel('频率偏移 (MHz)');
title('下扫频发射信号（基带）');
grid on;

% 子图3：上扫频差频信号
subplot(3,2,3);
plot(t(1:1000) * 1e6, real(beat_up_noisy(1:1000)), 'g-', 'LineWidth', 1);
xlabel('时间 (μs)');
ylabel('幅度');
title(sprintf('上扫频差频（实部，%.1f kHz）', f_beat_up / 1e3));
grid on;

% 子图4：下扫频差频信号
subplot(3,2,4);
plot(t(1:1000) * 1e6, real(beat_down_noisy(1:1000)), 'Color', [0.8 0.5 0], 'LineWidth', 1);
xlabel('时间 (μs)');
ylabel('幅度');
title(sprintf('下扫频差频（实部，%.1f kHz）', f_beat_down / 1e3));
grid on;

% 子图5：上扫频频谱
subplot(3,2,5);
plot(freq_signed / 1e3, spectrum_up_mag, 'b-', 'LineWidth', 1.5);
hold on;
plot(f_beat_up_measured / 1e3, spec_up_pos(idx_up_local), 'ro', 'MarkerSize', 8, ...
     'MarkerFaceColor', 'r');
xline(f_beat_up / 1e3, 'r--', 'LineWidth', 1.2);
xlabel('频率 (kHz)');
ylabel('幅度');
title('上扫频 FFT');
grid on;
xlim([-100, 100]);
y_limits = ylim;
text(f_beat_up / 1e3, y_limits(2) * 0.88, '理论值', ...
    'Color', 'r', 'FontSize', 10, 'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'bottom', 'BackgroundColor', 'w', 'Margin', 1);

% 子图6：下扫频频谱
subplot(3,2,6);
plot(freq_signed / 1e3, spectrum_down_mag, 'm-', 'LineWidth', 1.5);
hold on;
plot(f_beat_down_signed / 1e3, spec_down_neg(idx_down_local), 'ko', 'MarkerSize', 8, ...
     'MarkerFaceColor', 'k');
xline(-f_beat_down / 1e3, 'k--', 'LineWidth', 1.2);
xlabel('频率 (kHz)');
ylabel('幅度');
title(sprintf('下扫频 FFT（距离 %.1f m，速度 %.1f m/s）', R_measured, v_measured));
grid on;
xlim([-100, 100]);
y_limits = ylim;
text(-f_beat_down / 1e3, y_limits(2) * 0.88, '理论值', ...
    'Color', 'k', 'FontSize', 10, 'HorizontalAlignment', 'center', ...
    'VerticalAlignment', 'bottom', 'BackgroundColor', 'w', 'Margin', 1);

%% 性能指标
delta_R = c / (2 * B);
fprintf('性能指标：\n');
fprintf('  距离分辨率: %.2f m\n', delta_R);
fprintf('  最大探测距离: %.0f m (取决于采样率)\n', c * fs * T_chirp / (4 * B));
fprintf('\n仿真完成！\n');
