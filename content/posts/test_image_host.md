---
title: "测试图床和Typora"
date: 2025-03-13T23:01:00-07:00
draft: false
---



现在是从 Typora 编辑 markdown。



把一张图片复制到 Typora：

![FullSizeRender_VSCO 7](https://img.shuang.blog/2025/03/9c96bc55d21295e8b87cc7f8718eb1fb_watermarked_combined.png%207.JPG#wm:both)

然后等下 git commit 之前，git 会先执行一个 python 脚本，会把这个图片打上水印，并且替换为 CloudFlare 图床的链接。



刚才那张照片的路径里有空格，代码修改了下，再测一张有空格的照片：



![FullSizeRender_VSCO 8](test_image_host.assets/FullSizeRender_VSCO%208.JPG#wm::both)
