<template>
  <el-table :data="resumes" v-loading="loading">
    <el-table-column prop="basic_info.name" label="姓名" width="100" />
    <el-table-column prop="basic_info.phone" label="电话" width="140" />
    <el-table-column prop="file_name" label="文件名" />
    <el-table-column prop="file_type" label="类型" width="80" />
    <el-table-column label="技能" min-width="200">
      <template #default="{ row }">
        <el-tag
          v-for="skill in row.skills?.hard_skills?.slice(0, 3)"
          :key="skill"
          size="small"
          class="mr-1"
        >
          {{ skill }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="预警" width="100">
      <template #default="{ row }">
        <el-badge v-if="row.warnings?.length" :value="row.warnings.length" type="danger" />
        <span v-else class="text-gray-400">-</span>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="120">
      <template #default="{ row }">
        <el-button size="small" @click="$emit('view', row)">查看</el-button>
        <el-button size="small" type="danger" @click="$emit('delete', row.id)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { ResumeData } from '@/api/resume'

defineProps<{
  resumes: ResumeData[]
  loading: boolean
}>()

defineEmits(['view', 'delete'])
</script>
