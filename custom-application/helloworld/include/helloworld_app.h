#ifndef _HELLOWORLD_APP_H_
#define _HELLOWORLD_APP_H_

#define HELLOWORLD_DEV_PATH  "/dev/helloworld"

int helloworld_get_msg(const char *dev_path, char *out, size_t out_len);
int helloworld_set_msg(const char *dev_path, const char *text);

#endif /* _HELLOWORLD_APP_H_ */
