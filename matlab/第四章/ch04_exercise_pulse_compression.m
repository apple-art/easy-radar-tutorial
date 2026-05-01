%% ch04_exercise_pulse_compression.m
% 第4章练习：脉冲压缩与匹配滤波
% 对应教材：4.5 小练习
% 运行方式：在 MATLAB 中逐节运行（Ctrl+Enter），观察输出和图形

%% ========================================================
%  练习 1：改变信噪比
% =========================================================

clear; close all; clc;
rng(0);

c = 3e8;
fc = 10e9; %#ok<NASGU>
Tp = 10e-6;
B = 20e6;
fs = 100e6;
R0 = 15e3;

[tx, mf, ~, ~] = ch04_make_lfm_pulse(B, Tp, fs);
Ntx = numel(tx);
delay_samples = round(2 * R0 / c * fs);
Nfast = Ntx + delay_samples;
signal_power = mean(abs(tx).^2);

SNR_list = [10, 0, -10, -20];
figure('Position', [100, 100, 1400, 900]);

for idx = 1:length(SNR_list)
    SNR_dB = SNR_list(idx);
    noise_power = signal_power / (10^(SNR_dB / 10));
    noise_sigma = sqrt(noise_power);
    rx = ch04_build_target_scene(tx, delay_samples, 1.0, Nfast, noise_sigma);

    [range_profile, range_axis, group_delay] = ch04_range_compress(rx, mf, c, fs);
    [peak_value, idx_peak] = max(abs(range_profile));
    delay_est_samples = idx_peak - 1 - group_delay;
    R_est = c * delay_est_samples / (2 * fs);

    subplot(2, 2, idx);
    plot(range_axis / 1e3, abs(range_profile), 'b', 'LineWidth', 1.5);
    hold on;
    plot(R_est / 1e3, peak_value, 'ro', 'MarkerSize', 10, ...
        'MarkerFaceColor', 'yellow', 'LineWidth', 2);
    xlabel('距离 (km)');
    ylabel('幅度');
    title(sprintf('SNR = %d dB, 估计距离 = %.2f km', SNR_dB, R_est / 1e3));
    grid on;
    legend('距离像', '检测峰值', 'Location', 'best');
end

sgtitle('练习 1：不同信噪比下的脉冲压缩效果', 'FontSize', 14, 'FontWeight', 'bold');

fprintf('练习 1 完成：观察 SNR 越低，峰值越难从噪声中分辨。\n');
fprintf('即使在低信噪比下，匹配滤波仍能显著抬高主峰。\n\n');

%% ========================================================
%  练习 2：多目标场景
% =========================================================

c = 3e8;
fc = 10e9; %#ok<NASGU>
Tp = 10e-6;
B = 20e6;
fs = 100e6;
range_targets = [15e3, 15.02e3];
amp_targets = [1.0, 0.8];

[tx, mf, ~, ~] = ch04_make_lfm_pulse(B, Tp, fs);
delay_samples = round(2 * range_targets / c * fs);
Nfast = numel(tx) + max(delay_samples) + 100;

signal_power = mean(abs(tx).^2);
SNR_dB = -5;
noise_power = signal_power / (10^(SNR_dB / 10));
noise_sigma = sqrt(noise_power);
rx = ch04_build_target_scene(tx, delay_samples, amp_targets, Nfast, noise_sigma);

[range_profile, range_axis, ~] = ch04_range_compress(rx, mf, c, fs);
[~, locs] = findpeaks(abs(range_profile), 'MinPeakHeight', 0.5 * max(abs(range_profile)), ...
    'SortStr', 'descend');

detected_ranges = [];
if length(locs) >= 2
    locs = sort(locs(1:2));
    detected_ranges = range_axis(locs);
else
    fprintf('警告：只检测到一个峰值，两个目标无法分辨。\n');
end

figure('Position', [100, 100, 1200, 600]);
subplot(1,2,1);
plot(range_axis / 1e3, abs(range_profile), 'b', 'LineWidth', 1.5);
hold on;
if ~isempty(detected_ranges)
    plot(detected_ranges / 1e3, abs(range_profile(locs)), 'ro', 'MarkerSize', 10, ...
        'MarkerFaceColor', 'red', 'LineWidth', 2);
end
xlabel('距离 (km)');
ylabel('幅度');
title('匹配滤波后的距离像');
grid on;

subplot(1,2,2);
if ~isempty(detected_ranges)
    center_idx = round(mean(locs));
else
    [~, center_idx] = max(abs(range_profile));
end
zoom_half_width = 250;
idx_start = max(1, center_idx - zoom_half_width);
idx_end = min(length(range_profile), center_idx + zoom_half_width);
plot(range_axis(idx_start:idx_end) / 1e3, abs(range_profile(idx_start:idx_end)), ...
    'b', 'LineWidth', 2);
hold on;
if ~isempty(detected_ranges)
    plot(detected_ranges / 1e3, abs(range_profile(locs)), 'ro', 'MarkerSize', 12, ...
        'MarkerFaceColor', 'red', 'LineWidth', 2);
end
xlabel('距离 (km)');
ylabel('幅度');
title('峰值附近放大');
grid on;

sgtitle('练习 2：多目标场景（两个目标相距 20 m）', 'FontSize', 14, 'FontWeight', 'bold');

fprintf('=== 练习 2：多目标检测结果 ===\n');
fprintf('真实距离 1: %.2f km\n', range_targets(1) / 1e3);
fprintf('真实距离 2: %.2f km\n', range_targets(2) / 1e3);
fprintf('真实间隔: %.2f m\n', abs(diff(range_targets)));
fprintf('理论距离分辨率: %.2f m\n', c / (2 * B));
if ~isempty(detected_ranges)
    fprintf('估计距离 1: %.2f km\n', detected_ranges(1) / 1e3);
    fprintf('估计距离 2: %.2f km\n', detected_ranges(2) / 1e3);
    fprintf('估计间隔: %.2f m\n', abs(diff(detected_ranges)));
    fprintf('结论：两个目标成功分辨。\n\n');
else
    fprintf('结论：两个目标无法分辨。\n\n');
end

%% ========================================================
%  练习 3：改变带宽
% =========================================================

c = 3e8;
fc = 10e9; %#ok<NASGU>
Tp = 10e-6;
fs = 100e6;
range_targets = [15e3, 15.05e3];
amp_targets = [1.0, 1.0];
B_list = [5e6, 10e6, 20e6, 40e6];

figure('Position', [100, 100, 1400, 900]);

fprintf('=== 练习 3：带宽与分辨率 ===\n');
fprintf('目标间隔: %.1f m\n\n', abs(diff(range_targets)));

for idx = 1:length(B_list)
    B = B_list(idx);
    [tx, mf, ~, ~] = ch04_make_lfm_pulse(B, Tp, fs);
    delay_samples = round(2 * range_targets / c * fs);
    Nfast = numel(tx) + max(delay_samples) + 100;
    rx = ch04_build_target_scene(tx, delay_samples, amp_targets, Nfast, 0.1);

    [range_profile, range_axis, ~] = ch04_range_compress(rx, mf, c, fs);
    range_center = mean(range_targets);
    range_half_width = c * 3e-6 / 2;
    range_mask = range_axis >= (range_center - range_half_width) & range_axis <= (range_center + range_half_width);
    range_view = range_axis(range_mask);
    profile_view = abs(range_profile(range_mask));

    subplot(2, 2, idx);
    plot(range_view / 1e3, profile_view, 'b', 'LineWidth', 2);
    xlabel('距离 (km)');
    ylabel('幅度');
    title(sprintf('B = %.1f MHz, 分辨率 = %.1f m', B / 1e6, c / (2 * B)));
    grid on;

    [peaks, ~] = findpeaks(profile_view, 'MinPeakHeight', 0.3 * max(profile_view));
    if length(peaks) >= 2
        status_text = '可分辨';
        status_color = 'green';
        summary_text = '可分辨';
    else
        status_text = '不可分辨';
        status_color = 'red';
        summary_text = '不可分辨';
    end
    text(mean(range_view) / 1e3, max(profile_view) * 0.8, status_text, ...
        'FontSize', 12, 'Color', status_color, ...
        'HorizontalAlignment', 'center', 'FontWeight', 'bold');

    fprintf('B = %2.0f MHz, 分辨率 = %5.1f m, %s\n', B / 1e6, c / (2 * B), summary_text);
end
fprintf('\n结论：带宽越大，距离分辨率越高。\n\n');

sgtitle('练习 3：带宽对距离分辨率的影响（两目标相距 50 m）', ...
    'FontSize', 14, 'FontWeight', 'bold');

%% ========================================================
%  练习 4：旁瓣抑制
% =========================================================

clearvars -except ans;
close all; clc;

c = 3e8;
fc = 10e9; %#ok<NASGU>
Tp = 10e-6;
B = 20e6;
fs = 100e6;
R0 = 15e3;

[tx, mf_rect, ~, ~] = ch04_make_lfm_pulse(B, Tp, fs);
delay_samples = round(2 * R0 / c * fs);
Nfast = numel(tx) + delay_samples;
rx = ch04_build_target_scene(tx, delay_samples, 1.0, Nfast, 0.1);
mainlobe_half_samples = max(1, ceil(2 * fs / B));

figure('Position', [100, 100, 1400, 900]);

subplot(2,2,1);
[range_profile, range_axis, ~] = ch04_range_compress(rx, mf_rect, c, fs);
[~, idx_peak] = max(abs(range_profile));
reference_peak = max(abs(range_profile));
ch04_plot_profile_db(range_axis, range_profile, idx_peak, '无窗（矩形窗）', mainlobe_half_samples, reference_peak);

subplot(2,2,2);
window = hamming(numel(tx)).';
mf = conj(fliplr(tx .* window));
[range_profile, range_axis, ~] = ch04_range_compress(rx, mf, c, fs);
[~, idx_peak] = max(abs(range_profile));
ch04_plot_profile_db(range_axis, range_profile, idx_peak, '汉明窗', mainlobe_half_samples, reference_peak);

subplot(2,2,3);
window = hann(numel(tx)).';
mf = conj(fliplr(tx .* window));
[range_profile, range_axis, ~] = ch04_range_compress(rx, mf, c, fs);
[~, idx_peak] = max(abs(range_profile));
ch04_plot_profile_db(range_axis, range_profile, idx_peak, '汉宁窗', mainlobe_half_samples, reference_peak);

subplot(2,2,4);
window = blackman(numel(tx)).';
mf = conj(fliplr(tx .* window));
[range_profile, range_axis, ~] = ch04_range_compress(rx, mf, c, fs);
[~, idx_peak] = max(abs(range_profile));
ch04_plot_profile_db(range_axis, range_profile, idx_peak, '布莱克曼窗', mainlobe_half_samples, reference_peak);

sgtitle('练习 4：窗函数对旁瓣的抑制效果', 'FontSize', 14, 'FontWeight', 'bold');

fprintf('=== 练习 4：窗函数效果对比 ===\n');
fprintf('1. 矩形窗：旁瓣最高，主瓣最窄。\n');
fprintf('2. 汉明窗：旁瓣明显降低，主瓣略微展宽。\n');
fprintf('3. 汉宁窗：旁瓣和主瓣宽度都介于两者之间。\n');
fprintf('4. 布莱克曼窗：旁瓣最低，但主瓣最宽。\n');
fprintf('结论：加窗可以降低旁瓣，但会牺牲主瓣宽度。\n');

function [tx, mf, k, t_fast] = ch04_make_lfm_pulse(B, Tp, fs)
    t_fast = (0:round(Tp * fs)-1) / fs;
    k = B / Tp;
    tx = exp(1j * pi * k * t_fast.^2);
    mf = conj(fliplr(tx));
end

function rx = ch04_build_target_scene(tx, delay_samples, amplitudes, Nfast, noise_sigma)
    if nargin < 5
        noise_sigma = 0;
    end
    delay_samples = delay_samples(:).';
    amplitudes = amplitudes(:).';
    if isscalar(amplitudes)
        amplitudes = amplitudes * ones(size(delay_samples));
    end

    rx = zeros(1, Nfast);
    for target_idx = 1:length(delay_samples)
        idx = delay_samples(target_idx) + (1:numel(tx));
        rx(idx) = rx(idx) + amplitudes(target_idx) * tx;
    end

    if noise_sigma > 0
        rx = rx + noise_sigma * (randn(size(rx)) + 1j * randn(size(rx))) / sqrt(2);
    end
end

function [range_profile, range_axis, group_delay] = ch04_range_compress(rx, mf, c, fs)
    group_delay = floor(length(mf) / 2);
    range_profile = conv(rx, mf, 'same');
    range_axis = ((0:numel(rx)-1) - group_delay) * c / (2 * fs);
end

function ch04_plot_profile_db(range_axis, range_profile, idx_peak, title_str, mainlobe_half_samples, reference_peak)
    zoom_half_width = 250;
    idx_start = max(1, idx_peak - zoom_half_width);
    idx_end = min(length(range_profile), idx_peak + zoom_half_width);
    range_view = range_axis(idx_start:idx_end) / 1e3;
    profile_view = abs(range_profile(idx_start:idx_end));
    peak_value = max(profile_view);
    profile_view_db = 20 * log10(profile_view / peak_value);
    peak_loss_dB = 20 * log10(peak_value / reference_peak);

    plot(range_view, profile_view_db, 'b', 'LineWidth', 2);
    xlabel('距离 (km)');
    ylabel('幅度 (dB)');
    title(title_str);
    grid on;
    ylim([-80, 5]);

    [~, local_peak_idx] = max(profile_view_db);
    left_idx = 1:max(1, local_peak_idx - mainlobe_half_samples);
    right_idx = min(length(profile_view_db), local_peak_idx + mainlobe_half_samples):length(profile_view_db);
    sidelobe_region = unique([left_idx, right_idx]);
    sidelobe_region(sidelobe_region == local_peak_idx) = [];
    if ~isempty(sidelobe_region)
        max_sidelobe = max(profile_view_db(sidelobe_region));
        text(mean(range_view), -70, sprintf('最高旁瓣: %.1f dB', max_sidelobe), ...
            'FontSize', 10, 'Color', 'red', 'HorizontalAlignment', 'center');
    end
    text(mean(range_view), -62, sprintf('峰值损失: %.1f dB', peak_loss_dB), ...
        'FontSize', 10, 'Color', [0.2, 0.2, 0.8], 'HorizontalAlignment', 'center');
end
