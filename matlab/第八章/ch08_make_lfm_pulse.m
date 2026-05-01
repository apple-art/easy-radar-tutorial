function [tx, mf, k, t_fast] = ch08_make_lfm_pulse(B, Tp, fs)
    % 生成基带 LFM 脉冲及其匹配滤波器
    t_fast = (0:round(Tp * fs)-1) / fs;
    k = B / Tp;
    tx = exp(1j * pi * k * t_fast.^2);
    mf = conj(fliplr(tx));
end
