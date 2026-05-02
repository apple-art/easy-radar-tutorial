% 第八章示例1：单目标距离处理的最小可运行示例
clear; close all; clc;
rng(0);

% 基本参数：本例采用复包络基带模型，fc 只保留物理背景
c = 3e8;
fc = 10e9; %#ok<NASGU>
B = 10e6;
Tp = 20e-6;
fs = 20e6;
R0 = 6000;

% 生成基带 LFM 脉冲
[tx, mf] = ch08_make_lfm_pulse(B, Tp, fs);
Ntx = numel(tx);

% 目标距离 -> 双程时延 -> 离散延迟样点
delay_time = 2 * R0 / c;
delay_samples = round(delay_time * fs);
Nfast = Ntx + delay_samples + 200;

% 构造单目标回波：把发射脉冲平移到延迟位置，再叠加复高斯噪声
rx = zeros(1, Nfast);
rx(delay_samples + (1:Ntx)) = tx;
noise_sigma = 0.05;
rx = rx + noise_sigma * (randn(size(rx)) + 1j * randn(size(rx))) / sqrt(2);

% 匹配滤波与距离估计
[range_profile, range_axis, group_delay] = ch08_range_compress(rx, mf, c, fs);
[~, idx_peak] = max(abs(range_profile));
delay_est_samples = idx_peak - 1 - group_delay;
R_est = c * delay_est_samples / (2 * fs);

fprintf('真实距离: %.2f km\n', R0 / 1e3);
fprintf('估计距离: %.2f km\n', R_est / 1e3);

figure('Position', [100, 100, 1000, 600]);
subplot(2,1,1);
plot(real(rx), 'LineWidth', 1.0);
grid on;
title('接收回波（实部）');
xlabel('采样点'); ylabel('幅度');

subplot(2,1,2);
plot(range_axis / 1e3, abs(range_profile), 'LineWidth', 1.5); hold on;
plot(R_est / 1e3, abs(range_profile(idx_peak)), 'ro', 'MarkerSize', 8, 'LineWidth', 1.5);
grid on;
title('匹配滤波后的距离像');
xlabel('距离 (km)'); ylabel('幅度');
legend('距离像', '峰值');
