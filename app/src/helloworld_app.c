#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>

#include "helloworld_app.h"
#include "helloworld_ioctl.h"

int helloworld_get_msg(const char *dev_path, char *out, size_t out_len)
{
	struct helloworld_msg msg;
	int fd, ret;

	fd = open(dev_path, O_RDONLY);
	if (fd < 0)
		return -errno;

	ret = ioctl(fd, HELLOWORLD_IOC_GET_MSG, &msg);
	close(fd);
	if (ret < 0)
		return -errno;

	strncpy(out, msg.text, out_len - 1);
	out[out_len - 1] = '\0';
	return 0;
}

int helloworld_set_msg(const char *dev_path, const char *text)
{
	struct helloworld_msg msg;
	int fd, ret;

	memset(&msg, 0, sizeof(msg));
	strncpy(msg.text, text, sizeof(msg.text) - 1);

	fd = open(dev_path, O_WRONLY);
	if (fd < 0)
		return -errno;

	ret = ioctl(fd, HELLOWORLD_IOC_SET_MSG, &msg);
	close(fd);
	if (ret < 0)
		return -errno;

	return 0;
}

int main(int argc, char *argv[])
{
	char buf[128];
	int ret;

	if (argc > 1) {
		ret = helloworld_set_msg(HELLOWORLD_DEV_PATH, argv[1]);
		if (ret < 0) {
			fprintf(stderr, "set_msg failed: %s\n", strerror(-ret));
			return 1;
		}
	}

	ret = helloworld_get_msg(HELLOWORLD_DEV_PATH, buf, sizeof(buf));
	if (ret < 0) {
		fprintf(stderr, "get_msg failed on %s: %s\n", HELLOWORLD_DEV_PATH, strerror(-ret));
		return 1;
	}

	printf("%s\n", buf);
	return 0;
}
