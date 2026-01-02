<template>
  <el-upload
    class="w-full"
    drag
    :auto-upload="false"
    :on-change="handleChange"
    :show-file-list="false"
    accept=".pdf,.docx,.doc,.txt,.jpg,.jpeg,.png"
  >
    <el-icon class="text-4xl text-gray-400"><UploadFilled /></el-icon>
    <div class="el-upload__text">
      拖拽文件到此处，或 <em>点击上传</em>
    </div>
    <template #tip>
      <div class="el-upload__tip">
        支持 PDF、Word、TXT、图片格式，单文件不超过10MB
      </div>
    </template>
  </el-upload>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { uploadResume } from '@/api/resume'

const emit = defineEmits(['success'])

const handleChange = async (uploadFile: any) => {
  if (!uploadFile.raw) return

  const loading = ElMessage.info({ message: '正在解析...', duration: 0 })

  try {
    const result = await uploadResume(uploadFile.raw)
    loading.close()

    if (result.status === 'success') {
      ElMessage.success('解析成功')
      emit('success', result.data)
    } else {
      ElMessage.error(result.error || '解析失败')
    }
  } catch (e) {
    loading.close()
    ElMessage.error('上传失败')
  }
}
</script>
