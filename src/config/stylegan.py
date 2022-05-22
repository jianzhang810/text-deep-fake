import torch
from loguru import logger as info_logger
from src.disk import disk
from pathlib import Path
from src.logger.simple import Logger
from src.data.baseline import  BaselineDataset
from src.utils.download import download_data, unarchieve 
from src.models.stylegan import StyleBased_Generator
from src.training.stylegan import StyleGanTrainer
from src.storage.simple import Storage
from src.losses.perceptual import VGGPerceptualLoss
from src.losses.ocr import OCRLoss
from torchvision import models
from torchvision.models.resnet import BasicBlock
from torch.utils.data import DataLoader

class ContentResnet(models.ResNet):
    def _forward_impl(self, x):
        # See note [TorchScript super()]
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        #x = self.avgpool(x)
        #x = torch.flatten(x, 1)
        #x = self.fc(x)

        return x

class Config:
    def __init__(self):
        disk.login()

        device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
        info_logger.info(f'Using device: {device}')
        data_dir = Path("data/imgur")
        style_dir = data_dir / 'IMGUR5K_small'
        if not data_dir.exists():
            data_dir.mkdir()
            local_path = download_data(Path("data/IMGUR5K_small.tar"), data_dir)
            unarchieve(local_path)
        batch_size = 16
        train_dataloader = DataLoader(BaselineDataset(style_dir / 'train'), shuffle=True, batch_size = batch_size)
        val_dataloader = DataLoader(BaselineDataset(style_dir / 'val'), batch_size = batch_size)

        total_epochs = 500 #20
        model = StyleBased_Generator(dim_latent=512)
        #model.load_state_dict(torch.load('/content/text-deep-fake/checkpoints/stylegan_one_style_working/14/model'))
        model.to(device)
        style_embedder = models.resnet18()
        style_embedder.fc = torch.nn.Identity()
        style_embedder = style_embedder.to(device)
        content_embedder = ContentResnet(BasicBlock, [2, 2, 2, 2]).to(device)
        optimizer = torch.optim.AdamW(list(model.parameters()) + list(style_embedder.parameters()) + list(content_embedder.parameters()), 
                                      lr=1e-3, weight_decay=1e-6)
        scheduler = torch.optim.lr_scheduler.MultiStepLR(
            optimizer,
            milestones=list(range(0, total_epochs, 20)),
            gamma=0.2
        )

        
        ocr_coef = 0.2
        perceptual_coef = 0.8

        storage = Storage('checkpoints/stylegan_new_dimensions')

        logger = Logger(image_freq=100, project_name='StyleGan')

        self.trainer = StyleGanTrainer(
            model,
            style_embedder,
            content_embedder,
            optimizer,
            scheduler,
            train_dataloader,
            val_dataloader,
            storage,
            logger,
            total_epochs,
            device,
            ocr_coef,
            perceptual_coef,
            VGGPerceptualLoss(),
            OCRLoss()
        )

    def run(self):
        self.trainer.run()
