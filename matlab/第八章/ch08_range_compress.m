function [range_data, range_axis, group_delay] = ch08_range_compress(rx, mf, c, fs)
    % 对单脉冲或脉冲矩阵做匹配滤波，并生成距离轴
    group_delay = floor(length(mf) / 2);

    if isvector(rx)
        rx = rx(:).';
        range_data = conv(rx, mf, 'same');
        Nfast = numel(rx);
    else
        range_data = zeros(size(rx));
        for pulse_idx = 1:size(rx, 1)
            range_data(pulse_idx, :) = conv(rx(pulse_idx, :), mf, 'same');
        end
        Nfast = size(rx, 2);
    end

    range_axis = ((0:Nfast-1) - group_delay) * c / (2 * fs);
end
