%% ch02_exercise_signals.m
%  对应教材：第2章 小练习
%  功能：辅助练习2（频谱分析）和练习3（混叠判断）
%  运行环境：MATLAB R2016b 及以上

%% ====== 练习 2：从频谱读信息 ======
% 构造两个分量的信号，画出时域波形和频谱

fs = 1000;                      % 采样率 1000 Hz
t  = 0 : 1/fs : 1 - 1/fs;      % 时间轴 0~1 s

% 两个正弦分量：100 Hz (3V) + 250 Hz (1V)
s = 3*sin(2*pi*100*t) + 1*sin(2*pi*250*t);

% FFT 计算单边幅度谱
N       = length(s);
S       = fft(s);
amp     = (2/N) * abs(S(1:N/2+1));  % 单边归一化
freq    = (0:N/2) * fs / N;         % 频率轴

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
% 用 800 Hz 采样包含 100/300/500 Hz 的信号
% 500 Hz 超过奈奎斯特频率 400 Hz，会混叠到 300 Hz

fs_low = 800;                        % 采样率 800 Hz
t_low  = 0 : 1/fs_low : 1 - 1/fs_low;

% 先用高采样率生成"真实"信号（参考）
% 300 Hz 和 500 Hz 采用同相余弦，便于在 800 Hz 采样后叠加到同一个 300 Hz 频点
fs_ref = 5000;
t_ref  = 0 : 1/fs_ref : 1 - 1/fs_ref;
s_ref  = sin(2*pi*100*t_ref) + cos(2*pi*300*t_ref) + cos(2*pi*500*t_ref);

% 用 800 Hz 采样
s_sampled = sin(2*pi*100*t_low) + cos(2*pi*300*t_low) + cos(2*pi*500*t_low);

% 对采样后的信号做 FFT
N2      = length(s_sampled);
S2      = fft(s_sampled);
amp2    = (2/N2) * abs(S2(1:N2/2+1));
freq2   = (0:N2/2) * fs_low / N2;

figure('Name', '练习3：混叠演示');
subplot(2,1,1);
plot(t_ref, s_ref, 'Color', [0.7 0.7 0.7], 'LineWidth', 1);
hold on;
stem(t_low, s_sampled, 'b', 'filled', 'MarkerSize', 3);
xlabel('时间 (s)'); ylabel('振幅');
title(sprintf('800 Hz 采样（奈奎斯特频率 = %d Hz）', fs_low/2));
xlim([0, 0.1]);  % 只看前 0.1 秒，细节更清楚
legend('原始信号（5000 Hz 参考）', '800 Hz 采样点');
grid on;

subplot(2,1,2);
stem(freq2, amp2, 'r', 'filled', 'MarkerSize', 4);
xlabel('频率 (Hz)'); ylabel('幅度');
title('采样后的频谱 —— 500 Hz 混叠到了 300 Hz');
xlim([0, 400]);
grid on;

% 标注混叠
hold on;
text(300, max(amp2(freq2 > 290 & freq2 < 310))+0.05, ...
    '← 300 Hz 原有 + 500 Hz 混叠', 'Color', 'r', 'FontSize', 9);

%% ====== 练习 5：修改参数观察混叠 ======
% 这段代码演示 7 Hz 采样 5 Hz 信号的混叠
% 混叠频率 = fs - f = 7 - 5 = 2 Hz

f_signal = 5;
fs_demo  = 7;
duration = 2;  % 看 2 秒，让低频混叠更明显

t_fine = linspace(0, duration, 5000);
t_s    = 0 : 1/fs_demo : duration;

sig_ref   = sin(2*pi*f_signal*t_fine);
sig_samp  = sin(2*pi*f_signal*t_s);
sig_recon = interp1(t_s, sig_samp, t_fine, 'linear');

figure('Name', '练习5：7 Hz 采样 5 Hz 信号');
plot(t_fine, sig_ref, 'Color', [0.8 0.8 0.8], 'LineWidth', 1.5); hold on;
plot(t_fine, sig_recon, 'b--', 'LineWidth', 1.5);
plot(t_s, sig_samp, 'ro', 'MarkerSize', 6, 'MarkerFaceColor', 'r');
xlabel('时间 (s)'); ylabel('振幅');
title(sprintf('7 Hz 采样 5 Hz 信号 → 混叠频率 = %d Hz', fs_demo - f_signal));
legend('原始 5 Hz 信号', '重建信号（2 Hz 混叠）', '采样点');
grid on;



