<template>
  <div>
    <h1 class="text-2xl font-bold mb-4">仪表盘</h1>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <div class="text-gray-500">简历总数</div>
          <div class="text-3xl font-bold mt-2">0</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div class="text-gray-500">今日解析</div>
          <div class="text-3xl font-bold mt-2">0</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div class="text-gray-500">问答次数</div>
          <div class="text-3xl font-bold mt-2">0</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
