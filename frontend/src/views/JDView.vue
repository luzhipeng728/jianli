<template>
  <div class="animate-fade-in">
    <!-- Header Section -->
    <div class="card p-6 mb-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-primary-50 flex items-center justify-center">
            <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h3 class="section-title">岗位描述管理</h3>
            <p class="text-sm text-secondary-500">创建和管理岗位描述及面试配置</p>
          </div>
        </div>
        <button @click="openCreateDialog" class="btn-primary flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          新建岗位
        </button>
      </div>
    </div>

    <!-- JD List Section -->
    <div class="card">
      <div class="px-6 py-4 border-b border-secondary-100 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-secondary-100 flex items-center justify-center">
            <svg class="w-4 h-4 text-secondary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h3 class="font-semibold text-secondary-800">岗位列表</h3>
            <p class="text-xs text-secondary-500">共 {{ total }} 个岗位</p>
          </div>
        </div>
        <button @click="loadJDs" class="btn-secondary flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          刷新
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="p-12 flex flex-col items-center justify-center">
        <div class="w-10 h-10 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
        <p class="mt-4 text-sm text-secondary-500">加载中...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="!jdList.length" class="p-12 flex flex-col items-center justify-center">
        <svg class="w-16 h-16 text-secondary-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <p class="text-secondary-500 mb-4">暂无岗位描述</p>
        <button @click="openCreateDialog" class="btn-primary">创建第一个岗位</button>
      </div>

      <!-- JD Cards -->
      <div v-else class="p-6">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="jd in jdList"
            :key="jd.id"
            class="card p-5 hover:shadow-lg transition-shadow cursor-pointer border border-secondary-100"
            @click="viewJD(jd)"
          >
            <!-- Header -->
            <div class="flex items-start justify-between mb-3">
              <div class="flex-1">
                <h4 class="font-semibold text-secondary-900 mb-1">{{ jd.title }}</h4>
                <p class="text-sm text-secondary-500">{{ jd.department }}</p>
              </div>
              <el-dropdown @command="(command: string) => handleCommand(command, jd)">
                <button class="p-1 hover:bg-secondary-100 rounded transition-colors" @click.stop>
                  <svg class="w-5 h-5 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                  </svg>
                </button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit">编辑</el-dropdown-item>
                    <el-dropdown-item command="delete" class="text-red-600">删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <!-- Description -->
            <p class="text-sm text-secondary-600 mb-3 line-clamp-2">{{ jd.description }}</p>

            <!-- Skills -->
            <div class="flex flex-wrap gap-1.5 mb-3">
              <span
                v-for="skill in jd.required_skills.slice(0, 3)"
                :key="skill"
                class="px-2 py-0.5 text-xs rounded-full bg-primary-50 text-primary-700"
              >
                {{ skill }}
              </span>
              <span
                v-if="jd.required_skills.length > 3"
                class="px-2 py-0.5 text-xs rounded-full bg-secondary-100 text-secondary-600"
              >
                +{{ jd.required_skills.length - 3 }}
              </span>
            </div>

            <!-- Footer -->
            <div class="flex items-center justify-between text-xs text-secondary-400 pt-3 border-t border-secondary-100">
              <div class="flex items-center gap-1">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                {{ formatDate(jd.created_at) }}
              </div>
              <span class="px-2 py-0.5 rounded-full bg-secondary-100 text-secondary-600">
                {{ jd.interview_config.difficulty }}
              </span>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="total > 0" class="flex items-center justify-between mt-6 pt-4 border-t border-secondary-100">
          <span class="text-sm text-secondary-500">共 {{ total }} 个岗位</span>
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50]"
            :total="total"
            layout="sizes, prev, pager, next, jumper"
            @size-change="handlePageSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑岗位' : '新建岗位'"
      width="700px"
      :show-close="true"
      class="jd-dialog"
    >
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="120px" label-position="top">
        <!-- Basic Info -->
        <div class="mb-6">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-4">基本信息</h4>
          <el-form-item label="岗位名称" prop="title">
            <el-input v-model="formData.title" placeholder="请输入岗位名称，如：高级前端工程师" />
          </el-form-item>
          <el-form-item label="所属部门" prop="department">
            <el-input v-model="formData.department" placeholder="请输入部门名称，如：技术部" />
          </el-form-item>
          <el-form-item label="岗位描述" prop="description">
            <el-input
              v-model="formData.description"
              type="textarea"
              :rows="4"
              placeholder="请输入岗位描述，说明主要职责和工作内容"
            />
          </el-form-item>
        </div>

        <!-- Requirements -->
        <div class="mb-6">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-4">任职要求</h4>
          <el-form-item label="任职要求" prop="requirements">
            <div class="w-full space-y-2">
              <div
                v-for="(req, index) in formData.requirements"
                :key="index"
                class="flex items-center gap-2"
              >
                <el-input
                  v-model="formData.requirements[index]"
                  placeholder="请输入一条任职要求"
                />
                <button
                  @click="removeRequirement(index)"
                  class="p-2 text-red-500 hover:bg-red-50 rounded transition-colors"
                  type="button"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <button
                @click="addRequirement"
                class="w-full px-3 py-2 border border-dashed border-secondary-300 rounded-lg text-sm text-secondary-600 hover:border-primary-500 hover:text-primary-600 transition-colors"
                type="button"
              >
                + 添加要求
              </button>
            </div>
          </el-form-item>
        </div>

        <!-- Skills -->
        <div class="mb-6">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-4">技能要求</h4>
          <el-form-item label="必需技能" prop="required_skills">
            <el-select
              v-model="formData.required_skills"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="请输入必需技能，回车添加"
              class="w-full"
            >
            </el-select>
          </el-form-item>
          <el-form-item label="加分技能" prop="preferred_skills">
            <el-select
              v-model="formData.preferred_skills"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="请输入加分技能，回车添加"
              class="w-full"
            >
            </el-select>
          </el-form-item>
        </div>

        <!-- Interview Config -->
        <div class="mb-6">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-4">面试配置</h4>
          <div class="grid grid-cols-2 gap-4">
            <el-form-item label="笔试题数" prop="interview_config.written_question_count">
              <el-input-number
                v-model="formData.interview_config.written_question_count"
                :min="0"
                :max="50"
                class="w-full"
              />
            </el-form-item>
            <el-form-item label="语音面试时长(分钟)" prop="interview_config.voice_max_duration">
              <el-input-number
                v-model="formData.interview_config.voice_max_duration"
                :min="0"
                :max="120"
                class="w-full"
              />
            </el-form-item>
          </div>
          <el-form-item label="重点考察方向" prop="interview_config.focus_areas">
            <el-select
              v-model="formData.interview_config.focus_areas"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="请输入考察方向，回车添加"
              class="w-full"
            >
            </el-select>
          </el-form-item>
          <el-form-item label="难度等级" prop="interview_config.difficulty">
            <el-radio-group v-model="formData.interview_config.difficulty">
              <el-radio value="easy">简单</el-radio>
              <el-radio value="medium">中等</el-radio>
              <el-radio value="hard">困难</el-radio>
            </el-radio-group>
          </el-form-item>
        </div>
      </el-form>

      <template #footer>
        <div class="flex items-center justify-end gap-3">
          <button @click="dialogVisible = false" class="btn-secondary">取消</button>
          <button @click="handleSubmit" class="btn-primary">{{ isEdit ? '保存' : '创建' }}</button>
        </div>
      </template>
    </el-dialog>

    <!-- Detail Dialog -->
    <el-dialog
      v-model="detailDialogVisible"
      title=""
      width="700px"
      :show-close="true"
      class="jd-detail-dialog"
    >
      <template #header>
        <div class="flex items-center justify-between w-full">
          <div class="flex items-center gap-3">
            <div class="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center">
              <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <h2 class="text-xl font-bold text-secondary-900">{{ currentJD?.title }}</h2>
              <p class="text-sm text-secondary-500">{{ currentJD?.department }}</p>
            </div>
          </div>
        </div>
      </template>

      <template v-if="currentJD">
        <!-- Description -->
        <div class="card p-4 mb-4">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-3">岗位描述</h4>
          <p class="text-secondary-700 whitespace-pre-line">{{ currentJD.description }}</p>
        </div>

        <!-- Requirements -->
        <div class="card p-4 mb-4" v-if="currentJD.requirements?.length">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-3">任职要求</h4>
          <ul class="space-y-2">
            <li
              v-for="(req, index) in currentJD.requirements"
              :key="index"
              class="flex items-start gap-2 text-secondary-700"
            >
              <span class="text-primary-600 mt-0.5">•</span>
              <span>{{ req }}</span>
            </li>
          </ul>
        </div>

        <!-- Skills -->
        <div class="card p-4 mb-4">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-3">技能要求</h4>
          <div class="mb-3">
            <p class="text-xs text-secondary-500 mb-2">必需技能</p>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="skill in currentJD.required_skills"
                :key="skill"
                class="px-3 py-1 rounded-full text-sm bg-primary-50 text-primary-700"
              >
                {{ skill }}
              </span>
            </div>
          </div>
          <div v-if="currentJD.preferred_skills?.length">
            <p class="text-xs text-secondary-500 mb-2">加分技能</p>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="skill in currentJD.preferred_skills"
                :key="skill"
                class="px-3 py-1 rounded-full text-sm bg-secondary-100 text-secondary-700"
              >
                {{ skill }}
              </span>
            </div>
          </div>
        </div>

        <!-- Interview Config -->
        <div class="card p-4">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-3">面试配置</h4>
          <div class="grid grid-cols-2 gap-4">
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span class="text-secondary-700">笔试题数: {{ currentJD.interview_config.written_question_count }}</span>
            </div>
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span class="text-secondary-700">语音时长: {{ currentJD.interview_config.voice_max_duration }}分钟</span>
            </div>
          </div>
          <div class="mt-3">
            <p class="text-xs text-secondary-500 mb-2">重点考察方向</p>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="area in currentJD.interview_config.focus_areas"
                :key="area"
                class="px-2 py-1 rounded-md text-sm bg-blue-50 text-blue-700"
              >
                {{ area }}
              </span>
            </div>
          </div>
          <div class="mt-3">
            <p class="text-xs text-secondary-500 mb-2">难度等级</p>
            <span
              :class="[
                'px-3 py-1 rounded-full text-sm',
                currentJD.interview_config.difficulty === 'easy' ? 'bg-green-100 text-green-700' :
                currentJD.interview_config.difficulty === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'
              ]"
            >
              {{ difficultyText(currentJD.interview_config.difficulty) }}
            </span>
          </div>
        </div>

        <!-- Recommended Resumes -->
        <div class="card p-4 mt-4">
          <div class="flex items-center justify-between mb-3">
            <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider">
              推荐简历
              <span class="text-xs font-normal text-secondary-400 ml-2">共 {{ resumesTotal }} 份匹配</span>
            </h4>
            <span v-if="hasScreened" class="text-xs text-primary-600 bg-primary-50 px-2 py-1 rounded">
              已筛选 {{ minMatchScore }}% 以上
            </span>
          </div>

          <!-- AI Screening Controls -->
          <div class="bg-secondary-50 rounded-lg p-3 mb-4">
            <!-- Screening Progress -->
            <div v-if="isScreening && screeningStatus" class="mb-4">
              <!-- Overall Progress -->
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <div class="w-4 h-4 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
                  <span class="text-sm font-medium text-secondary-700">AI智能评分中...</span>
                </div>
                <span class="text-sm text-secondary-500">
                  {{ screeningStatus.completed || 0 }}/{{ screeningStatus.total || 0 }} 已完成
                </span>
              </div>
              <div class="w-full h-2 bg-secondary-200 rounded-full overflow-hidden mb-2">
                <div
                  class="h-full bg-gradient-to-r from-primary-500 to-primary-600 transition-all duration-300"
                  :style="{ width: `${screeningStatus.progress || 0}%` }"
                ></div>
              </div>

              <!-- Per-resume Progress List -->
              <div v-if="screeningStatus.resumes?.length" class="max-h-48 overflow-y-auto space-y-1 border border-secondary-200 rounded-lg p-2 bg-white">
                <div
                  v-for="task in screeningStatus.resumes.filter(r => r.status === 'processing' || r.status === 'queued').slice(0, 10)"
                  :key="task.resume_id"
                  class="flex items-center justify-between text-xs py-1 px-2 rounded"
                  :class="task.status === 'processing' ? 'bg-primary-50' : 'bg-secondary-50'"
                >
                  <div class="flex items-center gap-2 flex-1 min-w-0">
                    <div v-if="task.status === 'processing'" class="w-3 h-3 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin shrink-0"></div>
                    <span v-else class="w-3 h-3 rounded-full bg-secondary-300 shrink-0"></span>
                    <span class="truncate text-secondary-700">{{ task.resume_name || '未知' }}</span>
                  </div>
                  <div class="flex items-center gap-2 shrink-0 ml-2">
                    <span class="text-primary-600">{{ task.status_detail || (task.status === 'processing' ? 'AI评分中' : '等待中') }}</span>
                    <span class="text-secondary-400">{{ task.progress }}%</span>
                  </div>
                </div>
                <!-- Show completed count -->
                <div v-if="(screeningStatus.completed || 0) > 0" class="text-xs text-center text-green-600 py-1">
                  已完成 {{ screeningStatus.completed || 0 }} 份简历评分
                </div>
              </div>
            </div>

            <!-- Screening Controls -->
            <div class="flex items-center gap-4">
              <div class="flex items-center gap-2 flex-1">
                <span class="text-sm text-secondary-600 whitespace-nowrap">最低匹配分:</span>
                <el-slider
                  v-model="minMatchScore"
                  :min="0"
                  :max="100"
                  :step="5"
                  :show-tooltip="true"
                  :disabled="isScreening"
                  class="flex-1"
                />
                <span class="text-sm font-medium text-primary-600 w-12">{{ minMatchScore }}%</span>
              </div>
              <button
                @click="handleAIScreen"
                :disabled="resumesLoading || isScreening"
                class="btn-primary flex items-center gap-2 whitespace-nowrap"
              >
                <svg v-if="!isScreening" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <div v-else class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                {{ isScreening ? '评分中...' : 'AI智能评分' }}
              </button>
              <button
                v-if="hasScreened && !isScreening"
                @click="resetScreen"
                class="btn-secondary whitespace-nowrap"
              >
                重置
              </button>
            </div>
          </div>

          <!-- Loading -->
          <div v-if="resumesLoading" class="flex items-center justify-center py-6">
            <div class="w-6 h-6 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
            <span class="ml-2 text-sm text-secondary-500">{{ hasScreened ? 'AI筛选中...' : '加载中...' }}</span>
          </div>

          <!-- Empty -->
          <div v-else-if="!recommendedResumes.length" class="text-center py-6">
            <svg class="w-10 h-10 text-secondary-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="text-sm text-secondary-500">{{ hasScreened ? '没有符合条件的简历，请降低筛选分数' : '暂无匹配简历' }}</p>
          </div>

          <!-- Resume List -->
          <div v-else class="space-y-3">
            <div
              v-for="resume in recommendedResumes"
              :key="resume.resume_id"
              class="p-3 rounded-lg border border-secondary-100 hover:border-primary-200 hover:bg-primary-50/30 transition-all cursor-pointer"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="font-medium text-secondary-800">{{ resume.name }}</span>
                    <span
                      :class="[
                        'px-2 py-0.5 rounded-full text-xs font-medium',
                        resume.match_score >= 70 ? 'bg-green-100 text-green-700' :
                        resume.match_score >= 50 ? 'bg-yellow-100 text-yellow-700' :
                        'bg-secondary-100 text-secondary-600'
                      ]"
                    >
                      {{ resume.match_score }}%
                    </span>
                    <!-- Score breakdown -->
                    <span class="text-xs text-secondary-400" v-if="resume.skill_score">
                      技能{{ resume.skill_score }}% · 经验{{ resume.experience_score }}% · 学历{{ resume.education_score }}%
                    </span>
                  </div>
                  <p class="text-sm text-secondary-500 truncate mt-0.5">
                    {{ resume.latest_company }} · {{ resume.latest_title }}
                  </p>
                  <div class="flex flex-wrap gap-1 mt-1">
                    <span
                      v-for="skill in (resume.matched_skills || []).slice(0, 4)"
                      :key="skill"
                      class="px-1.5 py-0.5 text-xs rounded bg-green-50 text-green-600"
                    >
                      {{ skill }}
                    </span>
                    <span
                      v-for="skill in (resume.missing_skills || []).slice(0, 2)"
                      :key="skill"
                      class="px-1.5 py-0.5 text-xs rounded bg-red-50 text-red-500 line-through"
                    >
                      {{ skill }}
                    </span>
                  </div>
                  <!-- Highlights and Concerns -->
                  <div v-if="resume.highlights?.length || resume.concerns?.length" class="mt-2 text-xs">
                    <p v-if="resume.highlights?.length" class="text-green-600">
                      <span class="font-medium">亮点:</span> {{ resume.highlights.slice(0, 2).join('; ') }}
                    </p>
                    <p v-if="resume.concerns?.length" class="text-amber-600 mt-0.5">
                      <span class="font-medium">顾虑:</span> {{ resume.concerns.slice(0, 2).join('; ') }}
                    </p>
                  </div>
                </div>
                <div class="text-right text-xs text-secondary-400 ml-3 shrink-0">
                  <p>{{ resume.phone }}</p>
                  <p>{{ resume.education }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, reactive } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  getJDList, createJD, updateJD, deleteJD, getJD,
  startScreening, getScreeningStatus, getScreeningResults,
  type JobDescription, type ScreeningStatusResult, type ScreeningResult
} from '@/api/jd'

const jdList = ref<JobDescription[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const detailDialogVisible = ref(false)
const isEdit = ref(false)
const currentJD = ref<JobDescription | null>(null)
const formRef = ref<FormInstance>()

// 推荐简历相关
const recommendedResumes = ref<ScreeningResult[]>([])
const resumesLoading = ref(false)
const resumesTotal = ref(0)
const minMatchScore = ref(60)  // AI筛选最低分数
const hasScreened = ref(false) // 是否已执行AI筛选

// AI 筛选进度
const screeningStatus = ref<ScreeningStatusResult | null>(null)
const isScreening = ref(false)
const screeningPollingTimer = ref<number | null>(null)

const defaultFormData = {
  title: '',
  department: '',
  description: '',
  requirements: [''],
  required_skills: [],
  preferred_skills: [],
  interview_config: {
    written_question_count: 10,
    voice_max_duration: 30,
    focus_areas: [],
    difficulty: 'medium' as 'easy' | 'medium' | 'hard'
  }
}

const formData = reactive({ ...defaultFormData })

const rules: FormRules = {
  title: [{ required: true, message: '请输入岗位名称', trigger: 'blur' }],
  department: [{ required: true, message: '请输入所属部门', trigger: 'blur' }],
  description: [{ required: true, message: '请输入岗位描述', trigger: 'blur' }],
}

const loadJDs = async () => {
  loading.value = true
  try {
    const result = await getJDList(currentPage.value, pageSize.value)
    jdList.value = result.data || []
    total.value = result.total || 0
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  loadJDs()
}

const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  loadJDs()
}

const openCreateDialog = () => {
  isEdit.value = false
  Object.assign(formData, defaultFormData)
  formData.requirements = ['']
  formData.required_skills = []
  formData.preferred_skills = []
  formData.interview_config.focus_areas = []
  dialogVisible.value = true
}

const openEditDialog = async (jd: JobDescription) => {
  isEdit.value = true
  try {
    const detail = await getJD(jd.id)
    Object.assign(formData, detail)
    currentJD.value = detail
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

const viewJD = async (jd: JobDescription) => {
  // 重置筛选状态
  hasScreened.value = false
  minMatchScore.value = 60
  screeningStatus.value = null
  isScreening.value = false

  try {
    const detail = await getJD(jd.id)
    currentJD.value = detail
    detailDialogVisible.value = true
    // 检查是否有进行中的筛选任务
    await checkScreeningStatus(jd.id)
    // 如果不在筛选中，加载已有结果
    if (!isScreening.value) {
      loadRecommendedResumes(jd.id, 0)
    } else {
      // 如果在筛选中，开始轮询
      startScreeningPolling(jd.id)
    }
  } catch (error) {
    currentJD.value = jd
    detailDialogVisible.value = true
    loadRecommendedResumes(jd.id, 0)
  }
}

const loadRecommendedResumes = async (jdId: string, minScore: number = 0) => {
  resumesLoading.value = true
  recommendedResumes.value = []
  try {
    const result = await getScreeningResults(jdId, 1, 100, minScore)
    recommendedResumes.value = result.data || []
    resumesTotal.value = result.total || 0
    hasScreened.value = result.total > 0
  } catch (error) {
    console.error('加载推荐简历失败', error)
  } finally {
    resumesLoading.value = false
  }
}

// 检查筛选状态
const checkScreeningStatus = async (jdId: string) => {
  try {
    const status = await getScreeningStatus(jdId)
    screeningStatus.value = status

    const wasScreening = isScreening.value

    if (status.status === 'processing' || status.status === 'queued') {
      isScreening.value = true
    } else {
      isScreening.value = false
      stopScreeningPolling()
      // 筛选完成，加载结果（状态变为 success/idle 或 has_results 为 true）
      // 关键：当从 screening 状态变为非 screening 状态时，自动加载结果
      if (wasScreening || status.status === 'success' || status.has_results) {
        console.log('[Screening] 任务完成，加载结果', { wasScreening, status: status.status, hasResults: status.has_results })
        await loadRecommendedResumes(jdId, minMatchScore.value)
      }
    }
  } catch (error) {
    console.error('检查筛选状态失败', error)
  }
}

// 开始轮询筛选状态
const startScreeningPolling = (jdId: string) => {
  stopScreeningPolling()
  screeningPollingTimer.value = window.setInterval(() => {
    checkScreeningStatus(jdId)
  }, 1000)
}

// 停止轮询
const stopScreeningPolling = () => {
  if (screeningPollingTimer.value) {
    clearInterval(screeningPollingTimer.value)
    screeningPollingTimer.value = null
  }
}

// AI筛选功能
const handleAIScreen = async () => {
  if (!currentJD.value) return

  try {
    resumesLoading.value = true
    const result = await startScreening(currentJD.value.id, minMatchScore.value)

    if (result.status === 'queued' || result.status === 'processing') {
      isScreening.value = true
      ElMessage.info(result.message || '开始AI筛选...')
      startScreeningPolling(currentJD.value.id)
    } else if (result.status === 'success') {
      // 所有简历已有分析结果
      ElMessage.success(result.message || '筛选完成')
      await loadRecommendedResumes(currentJD.value.id, minMatchScore.value)
    }
  } catch (error) {
    ElMessage.error('启动AI筛选失败')
  } finally {
    resumesLoading.value = false
  }
}

// 重置筛选
const resetScreen = async () => {
  if (!currentJD.value) return
  hasScreened.value = false
  minMatchScore.value = 60
  recommendedResumes.value = []
  resumesTotal.value = 0
}

const addRequirement = () => {
  formData.requirements.push('')
}

const removeRequirement = (index: number) => {
  if (formData.requirements.length > 1) {
    formData.requirements.splice(index, 1)
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      // Filter out empty requirements
      const data = {
        ...formData,
        requirements: formData.requirements.filter(r => r.trim())
      }

      if (isEdit.value && currentJD.value) {
        await updateJD(currentJD.value.id, data)
        ElMessage.success('更新成功')
      } else {
        await createJD(data)
        ElMessage.success('创建成功')
      }

      dialogVisible.value = false
      loadJDs()
    } catch (error) {
      ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
    }
  })
}

const handleCommand = async (command: string, jd: JobDescription) => {
  if (command === 'edit') {
    openEditDialog(jd)
  } else if (command === 'delete') {
    await ElMessageBox.confirm('确定删除这个岗位？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    try {
      await deleteJD(jd.id)
      ElMessage.success('删除成功')
      loadJDs()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

const difficultyText = (difficulty: string) => {
  const map: Record<string, string> = {
    easy: '简单',
    medium: '中等',
    hard: '困难'
  }
  return map[difficulty] || difficulty
}

onMounted(loadJDs)

onUnmounted(() => {
  stopScreeningPolling()
})
</script>

<style>
.jd-dialog .el-dialog__header,
.jd-detail-dialog .el-dialog__header {
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
  margin-right: 0;
}

.jd-dialog .el-dialog__body,
.jd-detail-dialog .el-dialog__body {
  padding: 24px;
  max-height: 70vh;
  overflow-y: auto;
}

.jd-dialog .el-form-item {
  margin-bottom: 18px;
}

.jd-dialog .el-form-item__label {
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
