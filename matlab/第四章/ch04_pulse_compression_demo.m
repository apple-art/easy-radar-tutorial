%% ch04_pulse_compression_demo.m
% 第4章示例代码：脉冲压缩与距离测量
% 演示 LFM 信号生成、匹配滤波和目标距离计算

clear; close all; clc;
rng(0);

%% 参数设置
c = 3e8;               % 光速 (m/s)
fc = 10e9;             % 载频 (Hz)，这里只保留物理背景
Tp = 10e-6;            % 脉冲宽度 (s)
B = 20e6;              % 带宽 (Hz)
fs = 100e6;            % 采样率 (Hz)
R0 = 15e3;             % 目标真实距离 (m)

%% 生成 LFM 发射信号
[tx, mf, k, t_fast] = ch04_make_lfm_pulse(B, Tp, fs);
Ntx = numel(tx);

fprintf('=== 雷达参数 ===\n');
fprintf('载频: %.1f GHz\n', fc / 1e9);
fprintf('脉冲宽度: %.1f μs\n', Tp * 1e6);
fprintf('带宽: %.1f MHz\n', B / 1e6);
fprintf('调频斜率: %.2e Hz/s\n', k);
fprintf('时间-带宽积: %.0f\n', Tp * B);
fprintf('理论距离分辨率: %.2f m\n\n', c / (2 * B));

%% 模拟目标回波
delay_time = 2 * R0 / c;
delay_samples = round(delay_time * fs);
Nfast = Ntx + delay_samples;

signal_power = mean(abs(tx).^2);
SNR_dB = -10;
noise_power = signal_power / (10^(SNR_dB / 10));
noise_sigma = sqrt(noise_power);
rx = ch04_build_target_echo(tx, delay_samples, 1.0, Nfast, noise_sigma);

fprintf('=== 目标信息 ===\n');
fprintf('目标距离: %.2f km\n', R0 / 1e3);
fprintf('回波延迟: %.2f μs\n', delay_time * 1e6);
fprintf('延迟采样点数: %d\n\n', delay_samples);

fprintf('=== 信号质量 ===\n');
fprintf('信噪比: %.1f dB\n', SNR_dB);
fprintf('信号功率: %.2e\n', signal_power);
fprintf('噪声功率: %.2e\n\n', noise_power);

%% 匹配滤波与距离估计
[range_profile, range_axis, group_delay] = ch04_range_compress(rx, mf, c, fs);
[peak_value, idx_peak] = max(abs(range_profile));
delay_est_samples = idx_peak - 1 - group_delay;
R_est = c * delay_est_samples / (2 * fs);

peak_amplitude_gain = max(abs(range_profile)) / max(abs(rx));
peak_amplitude_gain_dB = 20 * log10(peak_amplitude_gain);
theoretical_processing_gain_dB = 10 * log10(Tp * B);
error_m = abs(R_est - R0);
error_percent = error_m / R0 * 100;

fprintf('=== 脉冲压缩效果 ===\n');
fprintf('主峰幅度抬升: %.1f (%.1f dB)\n', peak_amplitude_gain, peak_amplitude_gain_dB);
fprintf('理论处理增益(TB): %.1f (%.1f dB)\n\n', Tp * B, theoretical_processing_gain_dB);

fprintf('=== 距离测量结果 ===\n');
fprintf('真实距离: %.2f km\n', R0 / 1e3);
fprintf('估计距离: %.2f km\n', R_est / 1e3);
fprintf('绝对误差: %.2f m\n', error_m);
fprintf('相对误差: %.3f%%\n\n', error_percent);

%% 绘图
figure('Position', [100, 100, 1200, 800]);

subplot(3,2,1);
plot(t_fast * 1e6, real(tx), 'b', 'LineWidth', 1.5);
xlabel('时间 (μs)');
ylabel('幅度');
title('LFM 发射信号（实部）');
grid on;

subplot(3,2,2);
tx_spectrum = fftshift(abs(fft(tx)));
freq_axis = linspace(-fs / 2, fs / 2, length(tx_spectrum)) / 1e6;
plot(freq_axis, tx_spectrum, 'r', 'LineWidth', 1.5);
xlabel('频率 (MHz)');
ylabel('幅度');
title(sprintf('LFM 信号频谱（带宽 = %.1f MHz）', B / 1e6));
grid on;
xlim([-30, 30]);

subplot(3,2,3);
time_axis = (0:Nfast-1) / fs * 1e6;
plot(time_axis, abs(rx), 'Color', [0.5, 0.5, 0.5], 'LineWidth', 1);
xlabel('时间 (μs)');
ylabel('幅度');
title(sprintf('接收信号（SNR = %.1f dB）', SNR_dB));
grid on;

subplot(3,2,4);
plot(range_axis / 1e3, abs(range_profile), 'r', 'LineWidth', 1.5);
hold on;
plot(R_est / 1e3, peak_value, 'go', 'MarkerSize', 10, ...
    'MarkerFaceColor', 'yellow', 'LineWidth', 2);
xlabel('距离 (km)');
ylabel('幅度');
title('匹配滤波后的距离像');
legend('距离像', '检测峰值', 'Location', 'best');
grid on;

subplot(3,2,5);
zoom_half_width = 250;
idx_start = max(1, idx_peak - zoom_half_width);
idx_end = min(length(range_profile), idx_peak + zoom_half_width);
plot(range_axis(idx_start:idx_end) / 1e3, abs(range_profile(idx_start:idx_end)), ...
    'b', 'LineWidth', 2);
hold on;
plot(R_est / 1e3, peak_value, 'ro', 'MarkerSize', 12, ...
    'MarkerFaceColor', 'red', 'LineWidth', 2);
xlabel('距离 (km)');
ylabel('幅度');
title('峰值附近放大');
grid on;

subplot(3,2,6);
axis off;
text_str = {
    '测量结果总结：'
    ''
    sprintf('真实距离: %.2f km', R0 / 1e3)
    sprintf('估计距离: %.2f km', R_est / 1e3)
    sprintf('绝对误差: %.2f m', error_m)
    sprintf('相对误差: %.3f%%', error_percent)
    ''
    '脉冲压缩效果：'
    ''
    sprintf('主峰幅度抬升: %.1f dB', peak_amplitude_gain_dB)
    sprintf('理论处理增益: %.1f dB', theoretical_processing_gain_dB)
    sprintf('距离分辨率: %.2f m', c / (2 * B))
    ''
    '说明：'
    sprintf('主峰幅度抬升受噪声和输入峰值影响')
    sprintf('理论处理增益 TB 反映匹配滤波的理想上限')
};
text(0.1, 0.9, text_str, 'FontSize', 11, 'VerticalAlignment', 'top', ...
    'Interpreter', 'none', 'BackgroundColor', [0.95, 0.95, 0.95]);

sgtitle('第4章示例：脉冲压缩与距离测量', 'FontSize', 14, 'FontWeight', 'bold');

%% 保存结果
saveas(gcf, 'ch04_pulse_compression_demo.png');
fprintf('结果已保存为 ch04_pulse_compression_demo.png\n');

function [tx, mf, k, t_fast] = ch04_make_lfm_pulse(B, Tp, fs)
    t_fast = (0:round(Tp * fs)-1) / fs;
    k = B / Tp;
    tx = exp(1j * pi * k * t_fast.^2);
    mf = conj(fliplr(tx));
end

function rx = ch04_build_target_echo(tx, delay_samples, amplitude, Nfast, noise_sigma)
    if nargin < 5
        noise_sigma = 0;
    end
    rx = zeros(1, Nfast);
    rx(delay_samples + (1:numel(tx))) = amplitude * tx;
    if noise_sigma > 0
        rx = rx + noise_sigma * (randn(size(rx)) + 1j * randn(size(rx))) / sqrt(2);
    end
end

function [range_profile, range_axis, group_delay] = ch04_range_compress(rx, mf, c, fs)
    group_delay = floor(length(mf) / 2);
    range_profile = conv(rx, mf, 'same');
    range_axis = ((0:numel(rx)-1) - group_delay) * c / (2 * fs);
end
