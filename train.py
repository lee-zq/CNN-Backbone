import models
import torch, sys
import torchvision
import torchvision.transforms as transforms
import torch.optim as optim
import torch.nn as nn
import argparse, os
from utils.common import Logger, print_network

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

if __name__ == '__main__':

    # 命令行参数解析
    parser = argparse.ArgumentParser("CNN backbone on cifar10")
    parser.add_argument('--outf', default='./output/test_densenet', help='folder to output images and model checkpoints')  # 输出结果保存路径
    args = parser.parse_args()
    # 输入输出路径确认
    if not os.path.exists(args.outf):
        os.makedirs(args.outf)  # 创建输出文件夹
    sys.stdout = Logger(os.path.join(args.outf, 'train_log.txt'))  # 创建日志
    # 训练参数设置(可变参数建议用parser加载)
    EPOCH = 100  # 遍历数据集次数
    BATCH_SIZE = 128  # 批处理尺寸(batch_size)
    LR = 0.01  # 学习率
    # 数据集迭代器 建议数据提前下载并放到./Data目录下
    transform_train = transforms.Compose([
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])

    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    trainset = torchvision.datasets.CIFAR10(root='./Data', train=True,
                                            download=False, transform=transform_train)
    trainloader = torch.utils.data.DataLoader(trainset, batch_size=BATCH_SIZE,
                                              shuffle=True, num_workers=4)
    testset = torchvision.datasets.CIFAR10(root='./Data', train=False,
                                           download=False, transform=transform_test)
    testloader = torch.utils.data.DataLoader(testset, batch_size=BATCH_SIZE,
                                             shuffle=False, num_workers=4)
    classes = ('plane', 'car', 'bird', 'cat', 'deer',
               'dog', 'frog', 'horse', 'ship', 'truck')
    # 构建模型
    # net = models.LeNet()
    # net = models.Octresnet50(num_classes=10)
    # net = models.OctNet()
    # net = models.ghost_net()
    net = models.DenseNet(num_classes=10)
    # net = models.DeformLeNet()
    print_network(net)

    #loss函数
    criterion = nn.CrossEntropyLoss()  # 损失函数为交叉熵，多用于多分类问题
    optimizer = optim.Adam(net.parameters(), lr=LR)
    net.to(device)  # 转移到GPU

    # 训练过程
    best_acc = 0.00  # 初始化best test accuracy
    print("Start Training!")  # 定义遍历数据集的次数
    for epoch in range(EPOCH):
        # 训练一个Epoch
        print('\nTraining Epoch: %d' % (epoch + 1))
        net.train()  # 将net置为train模式（反向传播=True）
        sum_loss = 0.0  # 每个Epoch将累加的loss、corrent和样本数归零
        correct = 0.0
        total = 0.0
        for i, (inputs,labels) in enumerate(trainloader):  # 加载训练集
            # 准备数据
            length = len(trainloader)
            inputs, labels = inputs.to(device), labels.to(device)  # 训练数据导入到GPU
            optimizer.zero_grad()  # graph各节点grad置为0

            # forward + backward
            outputs = net(inputs)              # 前向传播
            loss = criterion(outputs, labels)  # 计算loss
            loss.backward()                    # 梯度反向传播
            optimizer.step()                   # 参数更新（优化）

            # 每训练1个batch打印一次loss和准确率(loss和准确率用已参加训练的数据的平均数计算)
            sum_loss += loss.item()  # 累加loss
            _, predicted = torch.max(outputs.data, dim=1)  # 取最大预测概率类为预测结果
            total += labels.size(0)     # 累加已参与训练的样本个数
            correct += predicted.eq(labels.data).cpu().sum() # 累加预测正确的样本个数
            if (i+1)%100 == 0:  # 每迭代100各batch打印一次训练结果
                print('[epoch:%d, iter:%d] Loss: %.03f | Acc: %.2f%% '
                    % (epoch + 1, (i + 1 + epoch * length), sum_loss / (i + 1), 100. * correct.item() / total))  # 输出当前训练结果

        # 每训练完一个Epoch测试一下准确率
        with torch.no_grad():  # 将pytorch置为不计算梯度模式
            correct = 0
            total = 0   # 计数归零（初始化）
            for data in testloader:  # 加载测试集
                net.eval()  # 将net置为评估模式（反向传播=False）
                images, labels = data
                images, labels = images.to(device), labels.to(device)  # 测试数据导入GPU
                outputs = net(images)  # 前向传播

                _, predicted = torch.max(outputs.data, dim=1)  # 取得分最高的那个类 (outputs.data的索引号)
                total += labels.size(0)                        # 累加样本总数
                correct += (predicted == labels).sum().item()        # 累加预测正确的样本个数
            acc = correct / total

            # 将最新的训练模型实时导出到文件
            print('Saving latest model......')
            torch.save(net.state_dict(), '%s/net_latest.pth' % (args.outf))
            # 将最佳测试分类准确率的模型写入net_best.pht文件文件中
            if acc > best_acc:
                print('Saving best model......')
                torch.save(net.state_dict(), '%s/net_best.pth' % (args.outf))
                best_acc = acc
            print('Test Acc is: %.2f%%' % (100*acc),'(Best Acc: %.2f%%)' % (100*best_acc))
    print("Training Finished, TotalEPOCH=%d" % EPOCH)