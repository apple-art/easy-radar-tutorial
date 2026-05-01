function [det_mask, row_idx, col_idx, range_est, vel_est] = ch08_detect_targets(rd_power, range_axis, vel_axis, threshold)
    % 固定阈值检测，并把检测点换回距离与速度坐标
    if nargin < 4 || isempty(threshold)
        threshold = 0.35;
    end

    det_mask = false(size(rd_power));
    [n_rows, n_cols] = size(rd_power);
    for row = 1:n_rows
        row_min = max(1, row - 1);
        row_max = min(n_rows, row + 1);
        for col = 1:n_cols
            if rd_power(row, col) <= threshold
                continue;
            end
            col_min = max(1, col - 1);
            col_max = min(n_cols, col + 1);
            neighborhood = rd_power(row_min:row_max, col_min:col_max);
            if rd_power(row, col) == max(neighborhood(:)) && nnz(neighborhood == rd_power(row, col)) == 1
                det_mask(row, col) = true;
            end
        end
    end
    [row_idx, col_idx] = find(det_mask);
    range_est = range_axis(col_idx);
    vel_est = vel_axis(row_idx);
end
