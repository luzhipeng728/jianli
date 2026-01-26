<template>
  <div class="animate-fade-in">
    <!-- Header -->
    <div class="card p-6 mb-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-primary-50 flex items-center justify-center">
            <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div>
            <h3 class="section-title">分析维度配置</h3>
            <p class="text-sm text-secondary-500">配置简历筛选、面试评估的分析维度和权重</p>
          </div>
        </div>
        <button @click="showCreateDialog = true" class="btn-primary flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          添加维度
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="card mb-6">
      <div class="px-6 py-4 border-b border-secondary-100">
        <div class="flex items-center gap-2">
          <button
            v-for="tab in tabs"
            :key="tab.value"
            @click="activeTab = tab.value"
            :class="[
              'px-4 py-2 text-sm font-medium rounded-lg transition-all',
              activeTab === tab.value
                ? 'bg-primary-50 text-primary-700 shadow-sm'
                : 'text-secondary-600 hover:bg-secondary-50'
            ]"
          >
            {{ tab.label }}
            <span
              :class="[
                'ml-2 px-2 py-0.5 rounded-full text-xs',
                activeTab === tab.value
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-secondary-100 text-secondary-600'
              ]"
            >
              {{ getDimensionCount(tab.value) }}
            </span>
          </button>
        </div>
      </div>

      <!-- Dimension List -->
      <div class="p-6">
        <!-- Loading -->
        <div v-if="loading" class="flex items-center justify-center py-12">
          <div class="flex flex-col items-center gap-4">
            <div class="w-10 h-10 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
            <span class="text-secondary-500">加载中...</span>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else-if="filteredDimensions.length === 0" class="text-center py-12">
          <svg class="w-16 h-16 mx-auto text-secondary-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p class="text-secondary-500 mb-4">暂无{{ tabs.find(t => t.value === activeTab)?.label }}维度</p>
          <button @click="showCreateDialog = true" class="btn-primary">
            添加维度
          </button>
        </div>

        <!-- Dimension Cards -->
        <div v-else class="space-y-4">
          <div
            v-for="dim in filteredDimensions"
            :key="dim.id"
            class="border border-secondary-200 rounded-lg p-4 hover:shadow-sm transition-all"
            :class="{ 'opacity-50': !dim.is_enabled }"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-2">
                  <h4 class="font-medium text-secondary-900">{{ dim.name }}</h4>
                  <span v-if="dim.is_default" class="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                    系统默认
                  </span>
                  <span v-if="!dim.is_enabled" class="px-2 py-0.5 text-xs bg-secondary-100 text-secondary-600 rounded-full">
                    已禁用
                  </span>
                  <span v-if="dim.weight > 0" class="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                    权重 {{ (dim.weight * 100).toFixed(0) }}%
                  </span>
                </div>
                <p class="text-sm text-secondary-600 mb-2">{{ dim.description || '暂无描述' }}</p>
                <p v-if="dim.prompt_hint" class="text-xs text-secondary-400">
                  <span class="font-medium">提示词：</span>{{ dim.prompt_hint }}
                </p>
              </div>
              <div class="flex items-center gap-2">
                <button
                  @click="toggleEnabled(dim)"
                  class="p-2 rounded-lg transition-colors"
                  :class="dim.is_enabled ? 'text-green-600 hover:bg-green-50' : 'text-secondary-400 hover:bg-secondary-50'"
                  :title="dim.is_enabled ? '禁用' : '启用'"
                >
                  <svg v-if="dim.is_enabled" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.542 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                </button>
                <button
                  @click="editDimension(dim)"
                  class="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                  title="编辑"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  v-if="!dim.is_default"
                  @click="handleDelete(dim)"
                  class="p-2 text-danger-600 hover:bg-danger-50 rounded-lg transition-colors"
                  title="删除"
                >
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Weight Summary -->
        <div v-if="activeTab !== 'parsing' && filteredDimensions.length > 0" class="mt-6 p-4 bg-secondary-50 rounded-lg">
          <div class="flex items-center justify-between">
            <span class="text-sm text-secondary-600">当前权重总计：</span>
            <span
              class="font-medium"
              :class="totalWeight === 1 ? 'text-green-600' : 'text-amber-600'"
            >
              {{ (totalWeight * 100).toFixed(0) }}%
              <span v-if="totalWeight !== 1" class="text-xs ml-1">(建议为100%)</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingDimension ? '编辑维度' : '添加维度'"
      width="500px"
    >
      <el-form :model="formData" label-width="80px">
        <el-form-item label="维度名称" required>
          <el-input v-model="formData.name" placeholder="如：团队协作能力" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="formData.type" class="w-full" :disabled="!!editingDimension">
            <el-option label="筛选维度（简历匹配）" value="screening" />
            <el-option label="评估维度（面试评价）" value="evaluation" />
            <el-option label="解析关注点（简历解析）" value="parsing" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="formData.type !== 'parsing'" label="权重">
          <el-slider v-model="formData.weightPercent" :min="0" :max="100" :step="5" show-input />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="formData.description" type="textarea" :rows="2" placeholder="简要描述这个维度的评估重点" />
        </el-form-item>
        <el-form-item label="提示词">
          <el-input v-model="formData.prompt_hint" type="textarea" :rows="3" placeholder="给AI的分析提示词，描述如何评估这个维度" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="flex justify-end gap-3">
          <button @click="showCreateDialog = false" class="btn-secondary">
            取消
          </button>
          <button @click="handleSave" class="btn-primary" :disabled="!formData.name || saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getDimensionList,
  createDimension,
  updateDimension,
  deleteDimension,
  type AnalysisDimension
} from '@/api/dimension'

const dimensions = ref<AnalysisDimension[]>([])
const loading = ref(false)
const saving = ref(false)
const activeTab = ref<'screening' | 'evaluation' | 'parsing'>('screening')
const showCreateDialog = ref(false)
const editingDimension = ref<AnalysisDimension | null>(null)

const tabs = [
  { label: '筛选维度', value: 'screening' as const },
  { label: '评估维度', value: 'evaluation' as const },
  { label: '解析关注点', value: 'parsing' as const }
]

const formData = ref({
  name: '',
  type: 'screening' as 'screening' | 'evaluation' | 'parsing',
  weightPercent: 10,
  description: '',
  prompt_hint: ''
})

const filteredDimensions = computed(() => {
  return dimensions.value.filter(d => d.type === activeTab.value)
})

const totalWeight = computed(() => {
  return filteredDimensions.value
    .filter(d => d.is_enabled)
    .reduce((sum, d) => sum + d.weight, 0)
})

const getDimensionCount = (type: string) => {
  return dimensions.value.filter(d => d.type === type).length
}

const loadDimensions = async () => {
  loading.value = true
  try {
    const result = await getDimensionList()
    dimensions.value = result.data || []
  } catch (error: any) {
    ElMessage.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const editDimension = (dim: AnalysisDimension) => {
  editingDimension.value = dim
  formData.value = {
    name: dim.name,
    type: dim.type,
    weightPercent: Math.round(dim.weight * 100),
    description: dim.description,
    prompt_hint: dim.prompt_hint
  }
  showCreateDialog.value = true
}

const resetForm = () => {
  editingDimension.value = null
  formData.value = {
    name: '',
    type: activeTab.value,
    weightPercent: 10,
    description: '',
    prompt_hint: ''
  }
}

const handleSave = async () => {
  if (!formData.value.name) {
    ElMessage.warning('请输入维度名称')
    return
  }

  saving.value = true
  try {
    const data = {
      name: formData.value.name,
      type: formData.value.type,
      weight: formData.value.weightPercent / 100,
      description: formData.value.description,
      prompt_hint: formData.value.prompt_hint
    }

    if (editingDimension.value) {
      await updateDimension(editingDimension.value.id, data)
      ElMessage.success('维度已更新')
    } else {
      await createDimension(data)
      ElMessage.success('维度已添加')
    }

    showCreateDialog.value = false
    resetForm()
    loadDimensions()
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const toggleEnabled = async (dim: AnalysisDimension) => {
  try {
    await updateDimension(dim.id, { is_enabled: !dim.is_enabled })
    dim.is_enabled = !dim.is_enabled
    ElMessage.success(dim.is_enabled ? '已启用' : '已禁用')
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  }
}

const handleDelete = async (dim: AnalysisDimension) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除维度"${dim.name}"吗？`,
      '确认删除',
      { type: 'warning' }
    )
    await deleteDimension(dim.id)
    ElMessage.success('维度已删除')
    loadDimensions()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

// Watch dialog close to reset form
const onDialogClose = () => {
  resetForm()
}

onMounted(() => {
  loadDimensions()
})
</script>
