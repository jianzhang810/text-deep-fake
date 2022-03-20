import time
from collections import defaultdict

from loguru import logger
from torch import Tensor
from typing import Optional, Dict
import wandb


class Logger():
    def __init__(self, print_freq: int = 100, image_freq: int = 1000, tb_path: str = None, project_name: str = None):
        self.print_freq: int = print_freq
        self.image_freq: int = image_freq
        self.loss_buff: dict[str, dict[str, list]] = defaultdict()
        self.loss_buff['values'] = defaultdict(list)
        self.loss_buff['sumlast'] = defaultdict(int)
        self.loss_buff['sum'] = defaultdict(int)
        self.metrics_buff: dict[str, dict[str, list]] = defaultdict()
        self.metrics_buff['values'] = defaultdict(list)
        self.metrics_buff['sumlast'] = defaultdict(int)
        self.metrics_buff['sum'] = defaultdict(int)
        self.tb_path: str = tb_path
        self.train_iter = 1
        self.val_iter = 1
        self.wandb = wandb.init(project=project_name, entity="text-deep-fake")

    def log_train(self, losses: Optional[Dict[str, float]] = None, images: Optional[Dict[str, Tensor]] = None):
        if self.train_iter == 1:
            self.start_time = time.time()
            logger.info(
                'Training started'
            )
        if losses:
            for loss_name, loss_value in losses.items():
                self.loss_buff['values'][loss_name] += [loss_value]
                self.loss_buff['sumlast'][loss_name] += loss_value
                self.wandb.log({f"{loss_name} loss": loss_value})

        if self.train_iter % self.print_freq == 0:
            self.end_time = time.time()
            logger.info(f'Batch: {self.train_iter}')
            logger.info(f'Processing time for last {self.print_freq} batches: {self.end_time - self.end_time:.3f}s')
            for loss_name in self.loss_buff["sumlast"]:
                logger.info(
                    f'Average {loss_name} loss over last {self.print_freq} batches: {self.loss_buff["sumlast"][loss_name] / self.print_freq}')
            logger.info('------------')
            self.start_time = self.end_time
            self.loss_buff['values'].clear()
            self.loss_buff['sumlast'].clear()

        if self.train_iter % self.image_freq == 0 and images:
            # TensorBoard magic
            pass

        self.train_iter += 1

    def log_val(self, losses: Optional[Dict[str, float]] = None,
                metrics: Optional[Dict[str, float]] = None, images: Optional[Dict[str, Tensor]] = None):

        if self.val_iter == 1:
            self.loss_buff['values'].clear()
            self.loss_buff['sumlast'].clear()
            logger.info(
                'Validation started'
            )
        if losses:
            for loss_name, loss_value in losses.items():
                self.loss_buff['values'][loss_name] += [loss_value]
                self.loss_buff['sum'][loss_name] += loss_value
                self.loss_buff['sumlast'][loss_name] += loss_value

        if metrics:
            for metric_name, metric_value in metrics.items():
                self.metrics_buff['values'][metric_name] += [metric_value]
                self.metrics_buff['sum'][metric_name] += metric_value
                self.metrics_buff['sumlast'][metric_name] += metric_value

        if self.val_iter % self.print_freq == 0:
            logger.info(f'Batch: {self.val_iter}')
            for loss_name in self.loss_buff["sumlast"]:
                logger.info(
                    f'Average {loss_name} loss over last {self.print_freq} batches: {self.loss_buff["sumlast"][loss_name] / self.print_freq}')
            self.loss_buff['values'].clear()
            self.loss_buff['sumlast'].clear()

            for metric_name in self.metrics_buff["sumlast"]:
                logger.info(
                    f'Average {metric_name} metric over last {self.print_freq} batches: {self.metrics_buff["sumlast"][metric_name] / self.print_freq}')
            self.metrics_buff['values'].clear()
            self.metrics_buff['sumlast'].clear()
            logger.info('------------')

        if self.val_iter % self.image_freq == 0:
            # TensorBoard magic
            pass

        self.val_iter += 1

    def end_val(self):
        avg_metrics = {}
        avg_losses = {}
        if self.loss_buff:
            for loss_name in self.loss_buff['sum']:
                logger.info(
                    f'Average {loss_name} over validation: {self.loss_buff["sum"][loss_name] / (self.val_iter - 1)}')
                avg_losses[loss_name] = self.loss_buff["sum"][loss_name] / (self.val_iter - 1)
        if self.metrics_buff:
            for metric_name in self.metrics_buff['sum']:
                logger.info(
                    f'Average {metric_name} over validation: {self.metrics_buff["sum"][metric_name] / (self.val_iter - 1)}')
                avg_metrics[metric_name] = self.metrics_buff["sum"][metric_name] / (self.val_iter - 1)

        for dict_name in self.loss_buff:
            self.loss_buff[dict_name].clear

        for dict_name in self.metrics_buff:
            self.metrics_buff[dict_name].clear()
        self.val_iter = 1
        self.train_iter = 1

        return avg_losses, avg_metrics
