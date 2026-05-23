%% ch02_exercise_signals.m
%  对应教材：第二版第2章 信号基础
%  功能：辅助第2章小练习，验证频谱、混叠、频率分辨率和 I/Q 样本
%  运行环境：MATLAB R2016b 及以上

%% ====== 练习 2：从频谱读信息 ======
% 构造 100 Hz 和 250 Hz 两个分量，观察时域波形和单边幅度谱。

fs = 1000;                      % 采样率 1000 Hz
t  = 0 : 1/fs : 1 - 1/fs;      % 时间轴 0~1 s

s = 3*sin(2*pi*100*t) + 1*sin(2*pi*250*t);

N    = length(s);
S    = fft(s);
amp  = (2/N) * abs(S(1:N/2+1));
freq = (0:N/2) * fs / N;

figure('Name', '练习2：时域波形与频谱');
subplot(2,1,1);
plot(t, s, 'b', 'LineWidth', 1.2);
xlabel('时间 (s)'); ylabel('振幅 (V)');
title('时域波形：100 Hz (3V) + 250 Hz (1V)');
grid on;

subplot(2,1,2);
stem(freq, amp, 'r', 'filled', 'MarkerSize', 4);
xlabel('频率 (Hz)'); ylabel('幅度 (V)');
title('频谱（单边幅度谱）');
xlim([0, 400]);
grid on;

%% ====== 练习 3：混叠判断 ======
% 用 800 Hz 采样包含 100/300/500 Hz 的信号。
% 奈奎斯特频率为 400 Hz，所以 500 Hz 会混叠到 300 Hz。

fs_low = 800;
t_low  = 0 : 1/fs_low : 1 - 1/fs_low;

fs_ref = 5000;
t_ref  = 0 : 1/fs_ref : 1 - 1/fs_ref;
s_ref  = sin(2*pi*100*t_ref) + cos(2*pi*300*t_ref) + cos(2*pi*500*t_ref);

s_sampled = sin(2*pi*100*t_low) + cos(2*pi*300*t_low) + cos(2*pi*500*t_low);

N2    = length(s_sampled);
S2    = fft(s_sampled);
amp2  = (2/N2) * abs(S2(1:N2/2+1));
freq2 = (0:N2/2) * fs_low / N2;

figure('Name', '练习3：混叠演示');
subplot(2,1,1);
plot(t_ref, s_ref, 'Color', [0.7 0.7 0.7], 'LineWidth', 1);
hold on;
stem(t_low, s_sampled, 'b', 'filled', 'MarkerSize', 3);
xlabel('时间 (s)'); ylabel('振幅');
title(sprintf('800 Hz 采样（奈奎斯特频率 = %d Hz）', fs_low/2));
xlim([0, 0.1]);
legend('原始信号（5000 Hz 参考）', '800 Hz 采样点');
grid on;

subplot(2,1,2);
stem(freq2, amp2, 'r', 'filled', 'MarkerSize', 4);
xlabel('频率 (Hz)'); ylabel('幅度');
title('采样后的频谱：500 Hz 混叠到 300 Hz');
xlim([0, 400]);
grid on;

hold on;
text(300, max(amp2(freq2 > 290 & freq2 < 310))+0.05, ...
    '<- 300 Hz 原有 + 500 Hz 混叠', 'Color', 'r', 'FontSize', 9);

%% ====== 练习 4：频率分辨率 ======
% 比较 0.05 s 与 0.08 s 观测时间下，1000 Hz 和 1015 Hz 是否能分开。

fs_res = 10000;
f1 = 1000;
f2 = 1015;

durations = [0.05, 0.08];
figure('Name', '练习4：频率分辨率');

for idx = 1:length(durations)
    Tobs = durations(idx);
    t_res = 0 : 1/fs_res : Tobs - 1/fs_res;
    x_res = sin(2*pi*f1*t_res) + sin(2*pi*f2*t_res);

    Nres = length(x_res);
    Xres = fft(x_res);
    amp_res = (2/Nres) * abs(Xres(1:floor(Nres/2)+1));
    freq_res = (0:floor(Nres/2)) * fs_res / Nres;

    subplot(2,1,idx);
    plot(freq_res, amp_res, 'LineWidth', 1.2);
    xlabel('频率 (Hz)'); ylabel('幅度');
    title(sprintf('观测时间 %.0f ms，频率间隔约 %.1f Hz', Tobs*1000, fs_res/Nres));
    xlim([940, 1080]);
    grid on;
end

%% ====== 练习 5：I/Q 样本的幅度与相位 ======
% 对复数样本 s = 3 + j4，计算幅度和相位，并画在 I/Q 平面上。

I = 3;
Q = 4;
z = I + 1j*Q;

amplitude = abs(z);
phase_rad = angle(z);
phase_deg = phase_rad * 180 / pi;

fprintf('I/Q 样本 z = %.1f + j%.1f\n', I, Q);
fprintf('幅度 = %.2f\n', amplitude);
fprintf('相位 = %.2f rad = %.1f deg\n', phase_rad, phase_deg);

figure('Name', '练习5：I/Q 样本');
plot([0, I], [0, Q], 'b-', 'LineWidth', 2);
hold on;
plot(I, Q, 'ro', 'MarkerSize', 8, 'MarkerFaceColor', 'r');
axis equal;
xlim([0, 5]); ylim([0, 5]);
grid on;
xlabel('I'); ylabel('Q');
title(sprintf('z = 3 + j4，幅度 = %.1f，相位 = %.1f°', amplitude, phase_deg));
