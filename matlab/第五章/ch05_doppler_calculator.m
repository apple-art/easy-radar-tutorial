% 第五章练习题：多普勒测速计算器
% 交互式计算工具，帮助理解多普勒效应

clear; close all; clc;

fprintf('========================================\n');
fprintf('   多普勒测速计算器\n');
fprintf('========================================\n\n');

%% 常用雷达频段
fprintf('常用雷达频段：\n');
fprintf('1. X波段: 10 GHz (军用、气象)\n');
fprintf('2. K波段: 24 GHz (测速枪、汽车雷达)\n');
fprintf('3. Ka波段: 35 GHz (测速枪)\n');
fprintf('4. W波段: 77 GHz (汽车防撞雷达)\n');
fprintf('5. S波段: 3 GHz (气象雷达)\n\n');

%% 示例1：从速度计算频移
fprintf('=== 示例1：从速度计算频移 ===\n');
f0 = 24e9;           % 24 GHz
v = 30;              % 30 m/s
c = 3e8;

delta_f = 2 * v * f0 / c;
fprintf('雷达频率: %.0f GHz\n', f0/1e9);
fprintf('目标速度: %.0f m/s (%.0f km/h)\n', v, v*3.6);
fprintf('多普勒频移: %.0f Hz\n\n', delta_f);

%% 示例2：从频移计算速度
fprintf('=== 示例2：从频移计算速度 ===\n');
f0 = 10e9;           % 10 GHz
delta_f = 3000;      % 3000 Hz

v = c * delta_f / (2 * f0);
fprintf('雷达频率: %.0f GHz\n', f0/1e9);
fprintf('多普勒频移: %.0f Hz\n', delta_f);
fprintf('目标速度: %.1f m/s (%.1f km/h)\n\n', v, v*3.6);

%% 示例3：角度影响
fprintf('=== 示例3：测量角度的影响 ===\n');
f0 = 24e9;
v_true = 30;         % 真实速度
theta = 30;          % 测量角度（度）

v_radial = v_true * cosd(theta);  % 径向速度
delta_f = 2 * v_radial * f0 / c;

fprintf('真实速度: %.0f m/s (%.0f km/h)\n', v_true, v_true*3.6);
fprintf('测量角度: %.0f°\n', theta);
fprintf('径向速度: %.1f m/s (%.1f km/h)\n', v_radial, v_radial*3.6);
fprintf('测得频移: %.0f Hz\n', delta_f);
fprintf('误差: %.1f%% (偏小)\n\n', (1-cosd(theta))*100);

%% 示例4：速度分辨率
fprintf('=== 示例4：速度分辨率 ===\n');
f0 = 35e9;           % 35 GHz
T = 0.2;             % 观测时间 0.2 s

delta_v = c / (2 * f0 * T);
fprintf('雷达频率: %.0f GHz\n', f0/1e9);
fprintf('观测时间: %.2f s\n', T);
fprintf('速度分辨率: %.3f m/s (%.2f km/h)\n\n', delta_v, delta_v*3.6);

%% 示例5：最大可测速度
fprintf('=== 示例5：最大可测速度 ===\n');
f0 = 77e9;           % 77 GHz
fs = 100e3;          % 采样率 100 kHz

% 这里采用连续波基带采样模型，按奈奎斯特频率估计速度上限
v_max = c * fs / (4 * f0);
fprintf('雷达频率: %.0f GHz\n', f0/1e9);
fprintf('采样率: %.0f kHz\n', fs/1e3);
fprintf('最大可测速度: %.1f m/s (%.1f km/h)\n\n', v_max, v_max*3.6);

%% 可视化：速度-频移关系
fprintf('=== 生成可视化图表 ===\n');

figure('Position', [100, 100, 1200, 800]);

% 子图1：不同频段的速度-频移关系
subplot(2,2,1);
v_range = 0:1:100;  % 速度范围 0-100 m/s
frequencies = [10e9, 24e9, 35e9, 77e9];
freq_labels = {'10 GHz', '24 GHz', '35 GHz', '77 GHz'};
colors = {'b', 'r', 'g', 'm'};

for i = 1:length(frequencies)
    delta_f_range = 2 * v_range * frequencies(i) / c;
    plot(v_range*3.6, delta_f_range/1e3, colors{i}, 'LineWidth', 2);
    hold on;
end
xlabel('速度 (km/h)');
ylabel('多普勒频移 (kHz)');
title('不同雷达频段的速度-频移关系');
legend(freq_labels, 'Location', 'northwest');
grid on;

% 子图2：角度对测量的影响
subplot(2,2,2);
theta_range = 0:1:90;  % 角度范围 0-90度
v_true = 30;  % 真实速度 30 m/s
v_measured = v_true * cosd(theta_range);
error_percent = (1 - cosd(theta_range)) * 100;

yyaxis left;
plot(theta_range, v_measured*3.6, 'b-', 'LineWidth', 2);
ylabel('测得速度 (km/h)');
ylim([0, 120]);

yyaxis right;
plot(theta_range, error_percent, 'r--', 'LineWidth', 2);
ylabel('误差 (%)');
ylim([0, 100]);

xlabel('测量角度 (度)');
title(sprintf('角度影响（真实速度 = %.0f km/h）', v_true*3.6));
grid on;
legend('测得速度', '误差', 'Location', 'east');

% 子图3：速度分辨率 vs 观测时间
subplot(2,2,3);
T_range = 0.01:0.01:1;  % 观测时间 0.01-1 s
f0 = 24e9;
delta_v_range = c ./ (2 * f0 * T_range);

plot(T_range*1000, delta_v_range*3.6, 'b-', 'LineWidth', 2);
xlabel('观测时间 (ms)');
ylabel('速度分辨率 (km/h)');
title('速度分辨率与观测时间的关系 (24 GHz)');
grid on;

% 子图4：最大可测速度 vs 采样率
subplot(2,2,4);
fs_range = 10e3:1e3:200e3;  % 采样率 10-200 kHz
f0 = 77e9;
v_max_range = c * fs_range / (4 * f0);

plot(fs_range/1e3, v_max_range*3.6, 'r-', 'LineWidth', 2);
xlabel('采样率 (kHz)');
ylabel('最大可测速度 (km/h)');
title('最大可测速度与采样率的关系 (77 GHz)');
grid on;

fprintf('图表已生成！\n\n');

%% 交互式计算器（可选）
fprintf('========================================\n');
fprintf('提示：可以修改代码中的参数进行自定义计算\n');
fprintf('========================================\n');
