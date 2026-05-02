function rx_matrix = ch08_simulate_echo_matrix(params, k)
    % 根据目标距离和速度构造脉冲回波矩阵
    fast_time = (0:params.Nfast-1) / params.fs;
    rx_matrix = zeros(params.Npulse, params.Nfast);
    warned_out_of_window = false(1, length(params.range_targets));

    for pulse_idx = 1:params.Npulse
        pulse_data = zeros(1, params.Nfast);
        for target_idx = 1:length(params.range_targets)
            tau = 2 * params.range_targets(target_idx) / params.c;
            fd = 2 * params.vel_targets(target_idx) / params.lambda;
            delayed_t = fast_time - tau;
            valid = delayed_t >= 0 & delayed_t < params.Tp;
            if ~any(valid)
                if ~warned_out_of_window(target_idx)
                    warning('Target %d at %.1f m is outside the fast-time window.', ...
                        target_idx, params.range_targets(target_idx));
                    warned_out_of_window(target_idx) = true;
                end
                continue;
            end

            echo = zeros(1, params.Nfast);
            echo(valid) = params.amp_targets(target_idx) ...
                * exp(1j * pi * k * delayed_t(valid).^2) ...
                .* exp(1j * 2 * pi * fd * (pulse_idx - 1) * params.Tr);
            pulse_data = pulse_data + echo;
        end

        noise = params.noise_sigma * (randn(1, params.Nfast) + 1j * randn(1, params.Nfast)) / sqrt(2);
        rx_matrix(pulse_idx, :) = pulse_data + noise;
    end
end
