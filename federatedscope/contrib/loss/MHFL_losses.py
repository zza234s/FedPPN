import torch
import torch.nn as nn


class ConLoss(nn.Module):
    """
    souce: https://github.com/yuetan031/FedPCL/blob/main/lib/losses.py
    """

    def __init__(self, temperature=0.07, contrast_mode='all',
                 base_temperature=0.07):
        super(ConLoss, self).__init__()
        self.temperature = temperature
        self.contrast_mode = contrast_mode
        self.base_temperature = base_temperature

    def forward(self, features, labels=None, global_protos=None, mask=None):
        """Compute contrastive loss between feature and global prototype
        """
        device = features.device

        if len(features.shape) < 3:
            raise ValueError('`features` needs to be [bsz, n_views, ...],'
                             'at least 3 dimensions are required')
        if len(features.shape) > 3:
            features = features.view(features.shape[0], features.shape[1], -1)

        batch_size = features.shape[0]
        if labels is not None and mask is not None:
            raise ValueError('Cannot define both `labels` and `mask`')
        elif labels is None and mask is None:
            mask = torch.eye(batch_size, dtype=torch.float32).to(device)
        elif labels is not None:
            labels = labels.contiguous().view(-1, 1)  # (32,1)
            if labels.shape[0] != batch_size:
                raise ValueError('Num of labels does not match num of features')
            mask = torch.eq(labels, labels.T).float().to(device)  # 生成一个对角矩阵？
            '''
                if labels = [7, 7, 6]
                此时的mask：  [1., 1., 0.],
                            [1., 1., 0.],
                            [0., 0., 1.]
            '''
        else:
            mask = mask.float().to(device)

        # contrast_count表示有几个view
        # 将两个view的features按照view排列
        contrast_count = features.shape[1]
        contrast_feature = torch.cat(torch.unbind(features, dim=1), dim=0)  # (8,2) #没看懂-->似乎就是构成的feature的f1,f2拼接起来
        if self.contrast_mode == 'one':
            anchor_feature = features[:, 0]
            anchor_count = 1
        elif self.contrast_mode == 'all':
            # anchor_feature = contrast_feature
            anchor_count = contrast_count
            anchor_feature = torch.zeros_like(contrast_feature)
        else:
            raise ValueError('Unknown mode: {}'.format(self.contrast_mode))

        # generate anchor_feature
        for i in range(batch_size * anchor_count):
            anchor_feature[i, :] = global_protos[labels[i % batch_size].item()]  # 每个样本标签对应的全局原型 （8，2）

        # compute logits
        anchor_dot_contrast = torch.div(
            torch.matmul(anchor_feature, contrast_feature.T),  # (8,8) 第(i,j)个元素代表，第i个样本的全局原型 与第j个样本的feature做向量乘法
            self.temperature)  # 8 x 8的矩阵每个元素除以 temperature
        # for numerical stability
        logits_max, _ = torch.max(anchor_dot_contrast, dim=1, keepdim=True)  # 8x1
        logits = anchor_dot_contrast - logits_max.detach()  # 8x8

        # tile mask
        mask = mask.repeat(anchor_count, contrast_count)
        # mask-out self-contrast cases
        logits_mask = torch.scatter(
            torch.ones_like(mask),
            1,
            torch.arange(batch_size * anchor_count).view(-1, 1).to(device),
            0
        )  # 8X8 矩阵，对角线为0，其余元素为1
        mask = mask * logits_mask

        # compute log_prob
        exp_logits = torch.exp(logits) * logits_mask
        log_prob = logits - torch.log(exp_logits.sum(1, keepdim=True))

        # compute mean of log-likelihood over positive
        mean_log_prob_pos = (mask * log_prob).sum(1) / mask.sum(1)

        # loss
        loss = - (self.temperature / self.base_temperature) * mean_log_prob_pos
        loss = loss.view(anchor_count, batch_size).mean()

        return loss
