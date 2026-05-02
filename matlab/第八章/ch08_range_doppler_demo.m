% 第八章示例2：距离处理与多普勒处理
clear; close all; clc;
rng(0);

params = ch08_default_scene();
data = ch08_run_processing_chain(params);

figure('Position', [120, 120, 1100, 700]);
subplot(2,1,1);
plot(data.range_axis / 1e3, abs(data.range_data(1, :)), 'LineWidth', 1.5);
grid on;
title('第一个脉冲的距离像');
xlabel('距离 (km)'); ylabel('幅度');

subplot(2,1,2);
imagesc(data.range_axis / 1e3, data.vel_axis, data.rd_power);
axis xy; colorbar;
title('距离-速度图');
xlabel('距离 (km)'); ylabel('速度 (m/s)');
