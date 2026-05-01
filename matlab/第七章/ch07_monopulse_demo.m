% 第七章实验3：单脉冲测角演示
% 演示和差波束单脉冲测角原理
clear; close all; clc;

% 基本参数
c = 3e8;
fc = 10e9;
lambda = c / fc;
D = 1.0;                    % 天线直径 (m)
beamwidth = lambda / D;     % 波束宽度 (弧度)
beamwidth_deg = beamwidth * 180 / pi;

% 目标参数
target_angle_true = 0.8;    % 目标真实角度 (度)

% 角度范围
theta_deg = -10:0.1:10;
theta_rad = theta_deg * pi / 180;

% 和波束（左右天线同相相加）
beam_left = exp(-4 * log(2) * ((theta_rad + beamwidth/4) / beamwidth).^2);
beam_right = exp(-4 * log(2) * ((theta_rad - beamwidth/4) / beamwidth).^2);
sum_beam = beam_left + beam_right;

% 差波束（右波束减左波束），这样右侧目标对应正单脉冲比
diff_beam = beam_right - beam_left;

% 目标在和波束和差波束上的响应
sum_response = interp1(theta_deg, sum_beam, target_angle_true);
diff_response = interp1(theta_deg, diff_beam, target_angle_true);

% 单脉冲比
monopulse_ratio = diff_response / sum_response;

% 单脉冲曲线（差/和 vs 角度）
monopulse_curve = diff_beam ./ sum_beam;

% 只在主瓣附近建立单调查找表，再反查角度
linear_mask = abs(theta_deg) <= beamwidth_deg;
[curve_sorted, sort_idx] = sort(monopulse_curve(linear_mask));
theta_lookup = theta_deg(linear_mask);
theta_lookup = theta_lookup(sort_idx);
estimated_angle = interp1(curve_sorted, theta_lookup, monopulse_ratio, 'linear', 'extrap');

% 绘图
figure('Position', [100, 100, 1200, 800]);

% 子图1：和波束与差波束
subplot(2,2,1);
plot(theta_deg, sum_beam, 'b-', 'LineWidth', 2); hold on;
plot(theta_deg, abs(diff_beam), 'r-', 'LineWidth', 2);
xline(target_angle_true, 'g--', 'LineWidth', 2);
grid on;
xlabel('角度 (度)');
ylabel('归一化幅度');
title('和波束与差波束');
legend('和波束 Σ', '差波束 |Δ|', '目标位置', 'Location', 'best');

% 子图2：单脉冲曲线
subplot(2,2,2);
plot(theta_deg, monopulse_curve, 'k-', 'LineWidth', 2); hold on;
plot(target_angle_true, monopulse_ratio, 'ro', 'MarkerSize', 10, 'LineWidth', 2);
plot(estimated_angle, monopulse_ratio, 'bx', 'MarkerSize', 12, 'LineWidth', 2);
xline(0, 'k--', 'LineWidth', 1);
yline(0, 'k--', 'LineWidth', 1);
grid on;
xlabel('角度 (度)');
ylabel('单脉冲比 Δ/Σ');
title('单脉冲曲线');
legend('单脉冲曲线', '真实位置', '估计位置', 'Location', 'best');
xlim([-10, 10]);
ylim([-1, 1]);

% 子图3：左右波束分量
subplot(2,2,3);
plot(theta_deg, beam_left, 'b-', 'LineWidth', 2); hold on;
plot(theta_deg, beam_right, 'r-', 'LineWidth', 2);
xline(target_angle_true, 'g--', 'LineWidth', 2);
grid on;
xlabel('角度 (度)');
ylabel('归一化幅度');
title('左右波束分量');
legend('左波束', '右波束', '目标位置', 'Location', 'best');

% 子图4：测角误差 vs 信噪比
subplot(2,2,4);
SNR_dB = 0:2:30;
SNR_linear = 10.^(SNR_dB / 10);

% 单脉冲测角精度（理论公式）
% σ_θ ≈ θ_3dB / (2 * sqrt(SNR))
angle_error_deg = beamwidth_deg ./ (2 * sqrt(SNR_linear));

semilogy(SNR_dB, angle_error_deg, 'b-', 'LineWidth', 2);
grid on;
xlabel('信噪比 (dB)');
ylabel('测角误差 (度)');
title('单脉冲测角精度 vs 信噪比');

% 输出结果
fprintf('========================================\n');
fprintf('单脉冲测角演示\n');
fprintf('========================================\n');
fprintf('波束宽度: %.2f°\n', beamwidth_deg);
fprintf('目标真实角度: %.2f°\n', target_angle_true);
fprintf('----------------------------------------\n');
fprintf('和波束响应 Σ: %.4f\n', sum_response);
fprintf('差波束响应 Δ: %.4f\n', diff_response);
fprintf('单脉冲比 Δ/Σ: %.4f\n', monopulse_ratio);
fprintf('----------------------------------------\n');
fprintf('估计角度: %.2f°\n', estimated_angle);
fprintf('测角误差: %.3f°\n', abs(estimated_angle - target_angle_true));
fprintf('========================================\n');
fprintf('说明：\n');
fprintf('- 单脉冲比为正 → 目标在右侧\n');
fprintf('- 单脉冲比为负 → 目标在左侧\n');
fprintf('- 单脉冲比为零 → 目标在中心\n');
fprintf('========================================\n');
