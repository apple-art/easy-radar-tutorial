% 第七章实验2：波束扫描测角演示
% 模拟机械扫描雷达探测目标角度的过程
clear; close all; clc;
rng(0);

% 基本参数
c = 3e8;
fc = 10e9;
lambda = c / fc;
D = 1.0;                    % 天线直径 (m)
beamwidth = lambda / D;     % 波束宽度 (弧度)

% 目标参数
target_angles = [15, 25];   % 两个目标的真实角度 (度)
target_rcs = [1.0, 0.8];    % 目标RCS (归一化)

% 扫描参数
scan_angles = -45:0.5:45;   % 扫描角度范围 (度)
scan_angles_rad = scan_angles * pi / 180;

% 计算每个扫描角度的回波强度
echo_power = zeros(size(scan_angles));

for i = 1:length(scan_angles)
    beam_center = scan_angles_rad(i);

    % 计算每个目标对当前波束指向的贡献
    for j = 1:length(target_angles)
        target_rad = target_angles(j) * pi / 180;
        angle_diff = target_rad - beam_center;

        % 天线方向图（高斯近似）
        antenna_gain = exp(-4 * log(2) * (angle_diff / beamwidth)^2);

        % 累加回波功率
        echo_power(i) = echo_power(i) + target_rcs(j) * antenna_gain;
    end
end

% 添加噪声
noise_level = 0.05;
echo_power = echo_power + noise_level * randn(size(echo_power));

% 寻找峰值（检测目标）
min_peak_height = 0.3;
min_peak_distance_deg = 0.8 * beamwidth * 180 / pi;
min_peak_distance_samples = max(1, round(min_peak_distance_deg / (scan_angles(2) - scan_angles(1))));
candidate_locs = 2:length(echo_power)-1;
is_peak = echo_power(candidate_locs) > echo_power(candidate_locs - 1) ...
       & echo_power(candidate_locs) >= echo_power(candidate_locs + 1) ...
       & echo_power(candidate_locs) > min_peak_height;
locs = candidate_locs(is_peak);

[~, sort_idx] = sort(echo_power(locs), 'descend');
selected_locs = [];
for idx = sort_idx
    loc = locs(idx);
    if isempty(selected_locs) || all(abs(loc - selected_locs) >= min_peak_distance_samples)
        selected_locs(end+1) = loc; %#ok<SAGROW>
    end
end
selected_locs = sort(selected_locs);
peaks = echo_power(selected_locs);
detected_angles = scan_angles(selected_locs);

% 绘图
figure('Position', [100, 100, 1200, 500]);

subplot(1,2,1);
plot(scan_angles, echo_power, 'b-', 'LineWidth', 1.5); hold on;
plot(detected_angles, peaks, 'ro', 'MarkerSize', 10, 'LineWidth', 2);
for j = 1:length(target_angles)
    xline(target_angles(j), 'g--', 'LineWidth', 2);
end
grid on;
xlabel('波束指向角度 (度)');
ylabel('回波功率 (归一化)');
title('扫描测角：回波功率 vs 波束指向');
legend('回波功率', '检测峰值', '真实目标', 'Location', 'best');

subplot(1,2,2);
polarplot(scan_angles_rad, echo_power, 'b-', 'LineWidth', 1.5); hold on;
polarplot(detected_angles * pi / 180, peaks, 'ro', 'MarkerSize', 10, 'LineWidth', 2);
title('极坐标显示');

% 输出结果
fprintf('波束宽度: %.2f°\n', beamwidth * 180 / pi);
fprintf('----------------------------------------\n');
fprintf('真实目标角度: ');
fprintf('%.1f° ', target_angles);
fprintf('\n');
fprintf('检测到的角度: ');
fprintf('%.1f° ', detected_angles);
fprintf('\n');
fprintf('----------------------------------------\n');
for i = 1:length(detected_angles)
    if i <= length(target_angles)
        error = abs(detected_angles(i) - target_angles(i));
        fprintf('目标%d: 真实 %.1f°, 检测 %.1f°, 误差 %.2f°\n', ...
            i, target_angles(i), detected_angles(i), error);
    end
end
