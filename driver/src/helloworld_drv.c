// SPDX-License-Identifier: GPL-2.0
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/mutex.h>
#include <linux/slab.h>

#include "helloworld_ioctl.h"

struct helloworld_priv {
	struct miscdevice miscdev;
	struct mutex lock;
	struct helloworld_msg msg;
};

static int helloworld_open(struct inode *inode, struct file *filp)
{
	struct miscdevice *miscdev = filp->private_data;
	struct helloworld_priv *priv = container_of(miscdev, struct helloworld_priv, miscdev);

	filp->private_data = priv;
	return 0;
}

static long helloworld_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
	struct helloworld_priv *priv = filp->private_data;
	void __user *argp = (void __user *)arg;
	int ret = 0;

	mutex_lock(&priv->lock);

	switch (cmd) {
	case HELLOWORLD_IOC_GET_MSG:
		if (copy_to_user(argp, &priv->msg, sizeof(priv->msg)))
			ret = -EFAULT;
		break;
	case HELLOWORLD_IOC_SET_MSG:
		if (copy_from_user(&priv->msg, argp, sizeof(priv->msg)))
			ret = -EFAULT;
		else
			priv->msg.text[sizeof(priv->msg.text) - 1] = '\0';
		break;
	default:
		ret = -ENOTTY;
	}

	mutex_unlock(&priv->lock);
	return ret;
}

static const struct file_operations helloworld_fops = {
	.owner          = THIS_MODULE,
	.open           = helloworld_open,
	.unlocked_ioctl = helloworld_ioctl,
};

static int helloworld_probe(struct platform_device *pdev)
{
	struct helloworld_priv *priv;
	int ret;

	priv = devm_kzalloc(&pdev->dev, sizeof(*priv), GFP_KERNEL);
	if (!priv)
		return -ENOMEM;

	mutex_init(&priv->lock);
	strscpy(priv->msg.text, "hello world", sizeof(priv->msg.text));

	priv->miscdev.minor = MISC_DYNAMIC_MINOR;
	priv->miscdev.name  = HELLOWORLD_DEV_NAME;
	priv->miscdev.fops  = &helloworld_fops;

	ret = misc_register(&priv->miscdev);
	if (ret) {
		dev_err(&pdev->dev, "misc_register failed: %d\n", ret);
		return ret;
	}

	platform_set_drvdata(pdev, priv);
	dev_info(&pdev->dev, "helloworld driver probed, /dev/%s ready\n", HELLOWORLD_DEV_NAME);
	return 0;
}

static int helloworld_remove(struct platform_device *pdev)
{
	struct helloworld_priv *priv = platform_get_drvdata(pdev);

	misc_deregister(&priv->miscdev);
	return 0;
}

static const struct of_device_id helloworld_of_match[] = {
	{ .compatible = "acme,helloworld" },
	{ }
};
MODULE_DEVICE_TABLE(of, helloworld_of_match);

static struct platform_driver helloworld_driver = {
	.probe  = helloworld_probe,
	.remove = helloworld_remove,
	.driver = {
		.name           = "helloworld",
		.of_match_table = helloworld_of_match,
	},
};
module_platform_driver(helloworld_driver);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("acme");
MODULE_DESCRIPTION("Jetson Orin Nano helloworld platform driver");
