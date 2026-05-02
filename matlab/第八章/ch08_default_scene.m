function params = ch08_default_scene()
    % 第八章默认场景参数：两目标脉冲雷达处理链
    params.c = 3e8;
    params.fc = 10e9;
    params.B = 10e6;
    params.Tp = 20e-6;
    params.fs = 20e6;
    params.PRF = 5e3;
    params.Npulse = 32;
    params.Nfast = 2048;
    params.range_targets = [6000, 9000];
    params.vel_targets = [30, -20];
    params.amp_targets = [1.0, 0.75];
    params.noise_sigma = 0.08;
    params.lambda = params.c / params.fc;
    params.Tr = 1 / params.PRF;
end
