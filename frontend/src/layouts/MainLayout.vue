<template>
  <el-container class="h-screen">
    <el-aside width="200px" class="bg-gray-900">
      <div class="p-4 text-white text-xl font-bold">
        智能简历助手
      </div>
      <el-menu
        :default-active="route.path"
        class="border-none"
        background-color="#111827"
        text-color="#9ca3af"
        active-text-color="#fff"
        router
      >
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/resume">
          <el-icon><Document /></el-icon>
          <span>简历解析</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能问答</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-main class="bg-gray-50 p-6">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>
