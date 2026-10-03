[app]
title = TurboTrack
package.name = turbotrack
package.domain = org.ankussingh
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.exclude_dirs = server,tests,bin,.github
version = 1.0.0
requirements = python3,kivy==2.3.0
orientation = portrait
fullscreen = 1

# Android
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
