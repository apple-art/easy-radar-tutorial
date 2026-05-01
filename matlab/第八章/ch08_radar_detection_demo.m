% 第八章示例3：距离-速度图上的简单阈值检测
clear; close all; clc;
rng(0);

params = ch08_default_scene();
data = ch08_run_processing_chain(params);

% 固定阈值判决，对应第六章的检测规则
threshold = 0.35;
[det_mask, ~, ~, range_est, vel_est] = ch08_detect_targets(...
    data.rd_power, data.range_axis, data.vel_axis, threshold);

figure('Position', [150, 150, 1000, 500]);
subplot(1,2,1);
imagesc(data.range_axis / 1e3, data.vel_axis, data.rd_power);
axis xy; colorbar;
title('距离-速度图');
xlabel('距离 (km)'); ylabel('速度 (m/s)');

subplot(1,2,2);
imagesc(data.range_axis / 1e3, data.vel_axis, data.rd_power);
axis xy; colorbar; hold on;
plot(range_est / 1e3, vel_est, 'ro', 'MarkerSize', 8, 'LineWidth', 1.5);
title('检测结果叠加');
xlabel('距离 (km)'); ylabel('速度 (m/s)');

fprintf('检测到的点数: %d\n', nnz(det_mask));
