% 第七章实验1：天线方向图与波束宽度
% 演示不同天线尺寸对波束宽度的影响
clear; close all; clc;

% 基本参数
c = 3e8;           % 光速 (m/s)
fc = 10e9;         % 工作频率 (Hz)
lambda = c / fc;   % 波长 (m)

% 三种不同的天线尺寸
D_array = [0.5, 1.0, 2.0];  % 天线直径 (m)
theta_deg = -90:0.1:90;     % 角度范围 (度)
theta_rad = theta_deg * pi / 180;

figure('Position', [100, 100, 1200, 400]);

for idx = 1:length(D_array)
    D = D_array(idx);

    % 计算理论波束宽度（弧度）
    beamwidth_rad = 0.886 * lambda / D;
    beamwidth_deg = beamwidth_rad * 180 / pi;

    % 计算归一化方向图（sinc 主瓣近似），避免工具箱版 sinc 依赖
    u = pi * D * sin(theta_rad) / lambda;
    pattern = ones(size(u));
    nonzero = abs(u) > 1e-12;
    pattern(nonzero) = abs(sin(u(nonzero)) ./ u(nonzero));
    pattern_dB = 20 * log10(pattern + 1e-10);

    % 用插值找到 3 dB 交点，减小角度网格造成的误差
    left_idx = find(theta_deg < 0 & pattern_dB <= -3, 1, 'last');
    right_idx = find(theta_deg > 0 & pattern_dB <= -3, 1, 'first');
    theta_3dB_left = interp1(pattern_dB([left_idx, left_idx+1]), theta_deg([left_idx, left_idx+1]), -3);
    theta_3dB_right = interp1(pattern_dB([right_idx-1, right_idx]), theta_deg([right_idx-1, right_idx]), -3);
    actual_beamwidth = theta_3dB_right - theta_3dB_left;

    % 绘图
    subplot(1, 3, idx);
    plot(theta_deg, pattern_dB, 'b-', 'LineWidth', 1.5); hold on;
    plot([theta_3dB_left, theta_3dB_right], [-3, -3], 'r--', 'LineWidth', 2);
    plot([theta_3dB_left, theta_3dB_left], [-40, -3], 'r--', 'LineWidth', 1);
    plot([theta_3dB_right, theta_3dB_right], [-40, -3], 'r--', 'LineWidth', 1);

    grid on;
    ylim([-40, 0]);
    xlabel('角度 (度)');
    ylabel('增益 (dB)');
    title(sprintf('天线直径 D = %.1f m\n3dB波束宽度 = %.2f°', D, actual_beamwidth));
    legend('方向图', '3dB线', 'Location', 'south');
end

sgtitle('天线尺寸对波束宽度的影响');

% 输出结果
fprintf('工作频率: %.1f GHz, 波长: %.2f cm\n', fc/1e9, lambda*100);
fprintf('----------------------------------------\n');
for idx = 1:length(D_array)
    D = D_array(idx);
    beamwidth_deg = (0.886 * lambda / D) * 180 / pi;
    fprintf('天线直径 %.1f m: 理论波束宽度 = %.2f°\n', D, beamwidth_deg);
end
