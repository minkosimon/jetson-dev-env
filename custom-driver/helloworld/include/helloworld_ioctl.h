#ifndef _HELLOWORLD_IOCTL_H_
#define _HELLOWORLD_IOCTL_H_

#include <linux/ioctl.h>

#define HELLOWORLD_DEV_NAME   "helloworld"
#define HELLOWORLD_IOC_MAGIC  'h'

struct helloworld_msg {
	char text[128];
};

/* lit le message courant conserve cote driver */
#define HELLOWORLD_IOC_GET_MSG   _IOR(HELLOWORLD_IOC_MAGIC, 1, struct helloworld_msg)
/* remplace le message courant */
#define HELLOWORLD_IOC_SET_MSG   _IOW(HELLOWORLD_IOC_MAGIC, 2, struct helloworld_msg)

#endif /* _HELLOWORLD_IOCTL_H_ */
