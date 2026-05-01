% 第八章完整示例：从回波矩阵到检测结果的完整处理链
clear; close all; clc;
rng(0);

params = ch08_default_scene();
data = ch08_run_processing_chain(params);

% 固定阈值检测，并把检测点换回物理量
threshold = 0.35;
[~, ~, ~, range_est, vel_est] = ch08_detect_targets(...
    data.rd_power, data.range_axis, data.vel_axis, threshold);

figure('Position', [100, 100, 1200, 800]);
subplot(2,2,1);
imagesc(real(data.rx_matrix)); colorbar;
title('原始回波矩阵（实部）');
xlabel('快时间采样点'); ylabel('脉冲序号');

subplot(2,2,2);
plot(data.range_axis / 1e3, abs(data.range_data(1, :)), 'LineWidth', 1.5); grid on;
title('第一个脉冲的距离像');
xlabel('距离 (km)'); ylabel('幅度');

subplot(2,2,3);
imagesc(data.range_axis / 1e3, data.vel_axis, data.rd_power);
axis xy; colorbar;
title('距离-速度图');
xlabel('距离 (km)'); ylabel('速度 (m/s)');

subplot(2,2,4);
imagesc(data.range_axis / 1e3, data.vel_axis, data.rd_power);
axis xy; colorbar; hold on;
plot(range_est / 1e3, vel_est, 'ro', 'MarkerSize', 8, 'LineWidth', 1.5);
title('检测结果叠加');
xlabel('距离 (km)'); ylabel('速度 (m/s)');

fprintf('检测到的目标（可能含相邻阈值点）:\n');
for idx = 1:length(range_est)
    fprintf('距离 = %.2f km, 速度 = %.2f m/s\n', range_est(idx) / 1e3, vel_est(idx));
end
