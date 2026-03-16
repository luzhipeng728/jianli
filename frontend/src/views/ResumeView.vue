<template>
  <div class="animate-fade-in">
    <!-- Upload Section -->
    <div class="card p-6 mb-6">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-primary-50 flex items-center justify-center">
            <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <div>
            <h3 class="section-title">上传简历</h3>
            <p class="text-sm text-secondary-500">支持 PDF、Word、TXT、图片格式</p>
          </div>
        </div>
        <!-- Upload Mode Toggle -->
        <div class="flex items-center gap-2 bg-secondary-100 rounded-lg p-1">
          <button
            @click="uploadMode = 'single'"
            :class="[
              'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
              uploadMode === 'single' ? 'bg-white text-primary-600 shadow-sm' : 'text-secondary-600 hover:text-secondary-800'
            ]"
          >
            单份上传
          </button>
          <button
            @click="uploadMode = 'batch'"
            :class="[
              'px-3 py-1.5 text-sm font-medium rounded-md transition-all',
              uploadMode === 'batch' ? 'bg-white text-primary-600 shadow-sm' : 'text-secondary-600 hover:text-secondary-800'
            ]"
          >
            批量上传
          </button>
        </div>
      </div>

      <!-- Single Upload -->
      <ResumeUploader v-if="uploadMode === 'single'" @success="handleUploadSuccess" />

      <!-- Batch Upload -->
      <BatchUploader v-else @success="handleBatchSuccess" />
    </div>

    <!-- Resume List Section -->
    <div class="card">
      <div class="px-6 py-4 border-b border-secondary-100 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-secondary-100 flex items-center justify-center">
            <svg class="w-4 h-4 text-secondary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h3 class="font-semibold text-secondary-800">简历列表</h3>
            <p class="text-xs text-secondary-500">共 {{ total }} 份简历 <span v-if="selectedIds.length > 0" class="text-primary-600">| 已选 {{ selectedIds.length }} 份</span></p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <!-- 批量操作按钮 -->
          <el-dropdown v-if="selectedIds.length > 0" @command="handleBatchCommand">
            <button class="btn-danger flex items-center gap-2">
              批量操作 ({{ selectedIds.length }})
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="delete">批量删除</el-dropdown-item>
                <el-dropdown-item command="export-json">导出 JSON</el-dropdown-item>
                <el-dropdown-item command="export-excel">导出 Excel</el-dropdown-item>
                <el-dropdown-item command="export-xml">导出 XML</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- 导出全部 -->
          <el-dropdown @command="handleExportCommand">
            <button class="btn-secondary flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              导出
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="json">导出 JSON</el-dropdown-item>
                <el-dropdown-item command="excel">导出 Excel</el-dropdown-item>
                <el-dropdown-item command="xml">导出 XML</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- 岗位匹配 -->
          <button @click="openMatchDialog" class="btn-secondary flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            岗位匹配
          </button>

          <button @click="loadResumes" class="btn-secondary flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            刷新
          </button>
        </div>
      </div>
      <div class="p-6">
        <ResumeList
          :resumes="resumes"
          :loading="loading"
          :selected-ids="selectedIds"
          :selectable="true"
          @view="handleView"
          @delete="handleDelete"
          @select="handleSelect"
          @select-all="handleSelectAll"
        />

        <!-- 分页 -->
        <div v-if="total > 0" class="flex items-center justify-between mt-6 pt-4 border-t border-secondary-100">
          <span class="text-sm text-secondary-500">共 {{ total }} 份简历</span>
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="total"
            layout="sizes, prev, pager, next, jumper"
            @size-change="handlePageSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </div>

    <!-- Detail Dialog -->
    <el-dialog
      v-model="dialogVisible"
      title=""
      width="700px"
      :show-close="true"
      class="resume-dialog"
    >
      <template #header>
        <div class="flex items-center justify-between w-full">
          <div class="flex items-center gap-3">
            <div class="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center">
              <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <div>
              <h2 class="text-xl font-bold text-secondary-900">{{ currentResume?.basic_info?.name || '简历详情' }}</h2>
              <p class="text-sm text-secondary-500">{{ currentResume?.file_name }}</p>
            </div>
          </div>
        </div>
      </template>

      <template v-if="currentResume">
        <!-- Source File Actions -->
        <div class="flex items-center justify-between p-4 mb-4 bg-gradient-to-r from-blue-50 to-green-50 rounded-xl border border-blue-100">
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span class="text-sm text-secondary-600">源文件: {{ currentResume.file_name }}</span>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="previewSourceFile"
              class="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors shadow-sm"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              在线预览
            </button>
            <button
              @click="downloadSourceFile"
              class="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors shadow-sm"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              下载文件
            </button>
          </div>
        </div>

        <!-- Basic Info -->
        <div class="card p-4 mb-4">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-3">基本信息</h4>
          <div class="grid grid-cols-2 gap-4">
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
              <span class="text-secondary-700">{{ currentResume.basic_info?.phone || '-' }}</span>
            </div>
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <span class="text-secondary-700">{{ currentResume.basic_info?.email || '-' }}</span>
            </div>
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span class="text-secondary-700">{{ currentResume.basic_info?.gender || '-' }}</span>
            </div>
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-secondary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span class="text-secondary-700">{{ currentResume.basic_info?.age ? `${currentResume.basic_info.age}岁` : '-' }}</span>
            </div>
          </div>
        </div>

        <!-- Education -->
        <div class="card p-4 mb-4" v-if="currentResume.education?.length">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-3">教育经历</h4>
          <div class="space-y-3">
            <div v-for="edu in currentResume.education" :key="edu.school" class="flex items-start gap-3">
              <div class="w-8 h-8 rounded-lg bg-primary-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                <svg class="w-4 h-4 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path d="M12 14l9-5-9-5-9 5 9 5z" /><path d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
                </svg>
              </div>
              <div class="flex-1">
                <div class="flex items-center gap-2">
                  <p class="font-medium text-secondary-800">{{ edu.school }}</p>
                  <!-- 学校验证状态标签 -->
                  <span v-if="edu.school_verified !== undefined" :class="[
                    'px-2 py-0.5 text-xs rounded-full',
                    edu.school_verified ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                  ]">
                    {{ edu.school_verified ? '✓ 已验证' : '⚠ 未验证' }}
                  </span>
                </div>
                <p class="text-sm text-secondary-500">{{ edu.degree }} · {{ edu.major }}</p>
                <p class="text-xs text-secondary-400" v-if="edu.start_date || edu.end_date">{{ edu.start_date }} - {{ edu.end_date }}</p>
                <!-- 数据来源佐证 -->
                <p v-if="edu.school_verification_source" class="text-xs text-secondary-400 mt-1">
                  <span class="text-primary-500">数据来源: {{ edu.school_verification_source }}</span>
                  <span v-if="edu.school_level" class="ml-2">{{ edu.school_level }}</span>
                </p>
                <p v-if="edu.school_verification_message && !edu.school_verified" class="text-xs text-amber-600 mt-1">
                  {{ edu.school_verification_message }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Experience -->
        <div class="card p-4 mb-4" v-if="currentResume.experience?.length">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-3">工作经历</h4>
          <div class="space-y-4">
            <div v-for="exp in currentResume.experience" :key="exp.company" class="border-l-2 border-primary-200 pl-4">
              <p class="font-medium text-secondary-800">{{ exp.company }}</p>
              <p class="text-sm text-primary-600">{{ exp.title }}</p>
              <p class="text-xs text-secondary-400 mb-2" v-if="exp.start_date || exp.end_date">{{ exp.start_date }} - {{ exp.end_date }}</p>
              <p class="text-sm text-secondary-600 whitespace-pre-line">{{ exp.duties }}</p>
            </div>
          </div>
        </div>

        <!-- Skills -->
        <div class="card p-4 mb-4" v-if="currentResume.skills?.hard_skills?.length || currentResume.skills?.soft_skills?.length">
          <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider mb-3">技能标签</h4>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="skill in currentResume.skills?.hard_skills"
              :key="skill"
              class="px-3 py-1 rounded-full text-sm bg-primary-50 text-primary-700"
            >
              {{ skill }}
            </span>
            <span
              v-for="skill in currentResume.skills?.soft_skills"
              :key="skill"
              class="px-3 py-1 rounded-full text-sm bg-secondary-100 text-secondary-700"
            >
              {{ skill }}
            </span>
          </div>
        </div>

        <!-- Dimension Analysis - AI多维度分析 -->
        <div class="card p-4 mb-4" v-if="currentResume.dimension_analysis && currentResume.dimension_analysis.dimensions?.length">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <svg class="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <h4 class="text-sm font-semibold text-secondary-500 uppercase tracking-wider">AI多维度分析</h4>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-2xl font-bold" :class="getScoreColorClass(currentResume.dimension_analysis.overall_score)">
                {{ currentResume.dimension_analysis.overall_score }}
              </span>
              <span class="text-sm text-secondary-500">综合评分</span>
            </div>
          </div>

          <!-- 综合评估 -->
          <div v-if="currentResume.dimension_analysis.summary" class="mb-4 p-3 bg-primary-50 rounded-lg">
            <p class="text-sm text-primary-900">{{ currentResume.dimension_analysis.summary }}</p>
          </div>

          <!-- 各维度评分 -->
          <div class="space-y-3 mb-4">
            <div v-for="dim in currentResume.dimension_analysis.dimensions" :key="dim.name" class="border-b border-secondary-100 pb-3 last:border-0">
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium text-secondary-700">{{ dim.name }}</span>
                <div class="flex items-center gap-2">
                  <span class="text-sm font-bold" :class="getScoreColorClass(dim.score)">{{ dim.score }}</span>
                  <span class="text-xs px-2 py-0.5 rounded" :class="getLevelClass(dim.level)">{{ dim.level }}</span>
                </div>
              </div>
              <!-- 进度条 -->
              <div class="w-full bg-secondary-200 rounded-full h-2 mb-2">
                <div class="h-2 rounded-full" :class="getScoreBarClass(dim.score)" :style="{ width: dim.score + '%' }"></div>
              </div>
              <!-- 亮点 -->
              <div v-if="dim.highlights?.length" class="flex flex-wrap gap-1">
                <span v-for="h in dim.highlights" :key="h" class="text-xs px-2 py-0.5 bg-green-100 text-green-800 rounded">
                  ✓ {{ h }}
                </span>
              </div>
              <!-- 问题 -->
              <div v-if="dim.concerns?.length" class="flex flex-wrap gap-1 mt-1">
                <span v-for="c in dim.concerns" :key="c" class="text-xs px-2 py-0.5 bg-amber-100 text-amber-800 rounded">
                  ⚠ {{ c }}
                </span>
              </div>
            </div>
          </div>

          <!-- 建议 -->
          <div v-if="currentResume.dimension_analysis.recommendations?.length" class="p-3 bg-blue-50 rounded-lg">
            <p class="text-xs font-semibold text-blue-900 mb-1">改进建议：</p>
            <ul class="text-xs text-blue-800 space-y-1">
              <li v-for="rec in currentResume.dimension_analysis.recommendations" :key="rec" class="flex items-start gap-1">
                <span>•</span>
                <span>{{ rec }}</span>
              </li>
            </ul>
          </div>
        </div>

        <!-- Education Warnings - 学历造假风险（重点突出） -->
        <div class="card p-4 border-red-300 bg-red-50 mb-4" v-if="currentResume.education_warnings?.length">
          <div class="flex items-center gap-2 mb-3">
            <svg class="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
            </svg>
            <h4 class="text-base font-bold text-red-800 uppercase tracking-wider">学历造假风险 ({{ currentResume.education_warnings.length }})</h4>
            <span class="ml-auto px-3 py-1 text-xs font-bold bg-red-600 text-white rounded-full animate-pulse">重点关注</span>
          </div>
          <div class="space-y-3">
            <div
              v-for="(warning, index) in currentResume.education_warnings"
              :key="index"
              :class="[
                'flex items-start gap-3 p-4 rounded-lg border-2',
                warning.risk_level === 'high' ? 'bg-red-100 border-red-400' :
                warning.risk_level === 'medium' ? 'bg-orange-100 border-orange-400' :
                'bg-yellow-100 border-yellow-400'
              ]"
            >
              <div class="flex-shrink-0">
                <span
                  :class="[
                    'inline-flex items-center justify-center w-8 h-8 rounded-full text-white text-xs font-bold',
                    warning.risk_level === 'high' ? 'bg-red-600' :
                    warning.risk_level === 'medium' ? 'bg-orange-500' :
                    'bg-yellow-500'
                  ]"
                >
                  {{ warning.risk_level === 'high' ? '高' : warning.risk_level === 'medium' ? '中' : '低' }}
                </span>
              </div>
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <span
                    :class="[
                      'px-2 py-0.5 text-xs font-semibold rounded',
                      warning.risk_level === 'high' ? 'bg-red-200 text-red-800' :
                      warning.risk_level === 'medium' ? 'bg-orange-200 text-orange-800' :
                      'bg-yellow-200 text-yellow-800'
                    ]"
                  >
                    {{ getEducationWarningTypeLabel(warning.type) }}
                  </span>
                </div>
                <p
                  :class="[
                    'text-sm font-medium',
                    warning.risk_level === 'high' ? 'text-red-900' :
                    warning.risk_level === 'medium' ? 'text-orange-900' :
                    'text-yellow-900'
                  ]"
                >
                  {{ warning.message }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Warnings -->
        <div class="card p-4 border-yellow-200 bg-yellow-50" v-if="currentResume.warnings?.length">
          <div class="flex items-center gap-2 mb-3">
            <svg class="w-5 h-5 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
            </svg>
            <h4 class="text-sm font-semibold text-yellow-800 uppercase tracking-wider">其他风险警告 ({{ currentResume.warnings.length }})</h4>
          </div>
          <div class="space-y-2">
            <div
              v-for="(warning, index) in currentResume.warnings"
              :key="index"
              class="flex items-start gap-2 p-3 bg-white border border-yellow-200 rounded-lg"
            >
              <span class="px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-700 rounded">{{ getWarningTypeLabel(warning.type) }}</span>
              <span class="text-sm text-yellow-800">{{ warning.message }}</span>
            </div>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- Preview Dialog -->
    <el-dialog
      v-model="previewDialogVisible"
      :title="currentResume?.file_name || '源文件预览'"
      width="90%"
      top="5vh"
      :show-close="true"
      class="preview-dialog"
    >
      <div class="preview-container">
        <!-- Loading -->
        <div v-if="previewLoading" class="flex items-center justify-center h-96">
          <div class="flex flex-col items-center gap-4">
            <div class="w-10 h-10 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
            <span class="text-secondary-500">加载中...</span>
          </div>
        </div>

        <!-- Error -->
        <div v-else-if="previewError" class="flex items-center justify-center h-96">
          <div class="flex flex-col items-center gap-4 text-center">
            <svg class="w-16 h-16 text-secondary-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-secondary-600">{{ previewError }}</p>
            <button @click="downloadSourceFile" class="btn-primary">下载文件查看</button>
          </div>
        </div>

        <!-- Preview Content -->
        <template v-else>
          <!-- PDF Preview -->
          <iframe
            v-if="previewType === 'pdf'"
            :src="previewUrl"
            class="w-full h-[80vh] border-0 rounded-lg"
          ></iframe>

          <!-- HTML Preview (for DOCX/DOC) -->
          <iframe
            v-else-if="previewType === 'html'"
            :src="previewUrl"
            class="w-full h-[80vh] border-0 rounded-lg bg-white"
          ></iframe>

          <!-- Image Preview -->
          <div v-else-if="previewType === 'image'" class="flex items-center justify-center">
            <img :src="previewUrl" class="max-w-full max-h-[80vh] object-contain rounded-lg shadow-lg" />
          </div>

          <!-- Text Preview -->
          <pre v-else-if="previewType === 'text'" class="bg-secondary-50 p-4 rounded-lg overflow-auto max-h-[80vh] text-sm">{{ previewText }}</pre>
        </template>
      </div>
    </el-dialog>

    <!-- Job Match Dialog -->
    <el-dialog
      v-model="matchDialogVisible"
      title="岗位匹配"
      width="800px"
      :show-close="true"
      class="match-dialog"
    >
      <el-form :model="matchForm" label-width="100px" label-position="top">
        <el-form-item label="岗位名称" required>
          <el-input v-model="matchForm.job_title" placeholder="请输入目标岗位名称，如：高级前端工程师" />
        </el-form-item>
        <el-form-item label="岗位描述">
          <el-input
            v-model="matchForm.job_description"
            type="textarea"
            :rows="3"
            placeholder="请输入岗位描述（可选）"
          />
        </el-form-item>
        <el-form-item label="必需技能">
          <el-select
            v-model="matchForm.required_skills"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="请输入必需技能，回车添加"
            class="w-full"
          />
        </el-form-item>
        <el-form-item label="优先技能">
          <el-select
            v-model="matchForm.preferred_skills"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="请输入优先技能，回车添加"
            class="w-full"
          />
        </el-form-item>
        <div class="grid grid-cols-2 gap-4">
          <el-form-item label="最低工作年限">
            <el-input-number v-model="matchForm.min_experience_years" :min="0" :max="30" class="w-full" />
          </el-form-item>
          <el-form-item label="学历要求">
            <el-select v-model="matchForm.education_level" placeholder="请选择" class="w-full">
              <el-option label="不限" value="" />
              <el-option label="大专" value="大专" />
              <el-option label="本科" value="本科" />
              <el-option label="硕士" value="硕士" />
              <el-option label="博士" value="博士" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item>
          <el-checkbox v-model="matchForm.use_ai">使用 AI 智能匹配（更准确但较慢）</el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="flex items-center justify-end gap-3">
          <button @click="matchDialogVisible = false" class="btn-secondary">取消</button>
          <button @click="handleMatch" :disabled="matchLoading || !matchForm.job_title" class="btn-primary">
            {{ matchLoading ? '匹配中...' : '开始匹配' }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- Match Results Dialog -->
    <el-dialog
      v-model="matchResultsVisible"
      title="匹配结果"
      width="900px"
      :show-close="true"
      class="match-results-dialog"
    >
      <div v-if="matchResults.length > 0" class="space-y-4">
        <div class="text-sm text-secondary-500 mb-4">共匹配到 {{ matchResults.length }} 份简历</div>
        <div
          v-for="result in matchResults"
          :key="result.resume_id"
          class="card p-4 border border-secondary-100"
        >
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-bold">
                {{ result.match_score }}
              </div>
              <div>
                <h4 class="font-semibold text-secondary-800">{{ result.name }}</h4>
                <p class="text-sm text-secondary-500">{{ result.phone }} | {{ result.email }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2 text-sm">
              <span class="px-2 py-1 rounded bg-blue-50 text-blue-700">技能 {{ result.skill_score }}</span>
              <span class="px-2 py-1 rounded bg-green-50 text-green-700">经验 {{ result.experience_score }}</span>
            </div>
          </div>
          <div v-if="result.matched_skills?.length" class="mb-2">
            <span class="text-xs text-secondary-500">匹配技能：</span>
            <span v-for="skill in result.matched_skills" :key="skill" class="ml-1 px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700">{{ skill }}</span>
          </div>
          <div v-if="result.missing_skills?.length" class="mb-2">
            <span class="text-xs text-secondary-500">缺失技能：</span>
            <span v-for="skill in result.missing_skills" :key="skill" class="ml-1 px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700">{{ skill }}</span>
          </div>
          <div v-if="result.highlights?.length" class="text-sm text-green-600">
            <span v-for="(h, i) in result.highlights" :key="i">{{ h }}{{ i < result.highlights.length - 1 ? ' | ' : '' }}</span>
          </div>
          <div v-if="result.concerns?.length" class="text-sm text-yellow-600">
            <span v-for="(c, i) in result.concerns" :key="i">{{ c }}{{ i < result.concerns.length - 1 ? ' | ' : '' }}</span>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-12 text-secondary-500">
        没有匹配的简历
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ResumeUploader from '@/components/resume/ResumeUploader.vue'
import BatchUploader from '@/components/resume/BatchUploader.vue'
import ResumeList from '@/components/resume/ResumeList.vue'
import {
  getResumeList,
  deleteResume,
  getResumeDetail,
  batchDeleteResumes,
  exportResumes,
  batchMatchJob,
  type ResumeData,
  type BatchMatchResultItem
} from '@/api/resume'

const resumes = ref<ResumeData[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const currentResume = ref<ResumeData | null>(null)
const uploadMode = ref<'single' | 'batch'>('single')

// 分页状态
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 选择状态
const selectedIds = ref<string[]>([])

// Preview state
const previewDialogVisible = ref(false)
const previewUrl = ref('')
const previewType = ref<'pdf' | 'image' | 'text' | 'html' | ''>('')
const previewLoading = ref(false)
const previewError = ref('')
const previewText = ref('')

// 岗位匹配状态
const matchDialogVisible = ref(false)
const matchLoading = ref(false)
const matchResultsVisible = ref(false)
const matchResults = ref<BatchMatchResultItem[]>([])
const matchForm = reactive({
  job_title: '',
  job_description: '',
  required_skills: [] as string[],
  preferred_skills: [] as string[],
  min_experience_years: 0,
  education_level: '',
  use_ai: false
})

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

const loadResumes = async () => {
  loading.value = true
  try {
    const result = await getResumeList(currentPage.value, pageSize.value)
    resumes.value = result.data || []
    total.value = result.total || 0
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  loadResumes()
}

const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  loadResumes()
}

const handleUploadSuccess = (data: ResumeData) => {
  resumes.value.unshift(data)
}

const handleBatchSuccess = (data: { total: number; success: number; failed: number }) => {
  // 批量上传成功后刷新列表
  loadResumes()
}

const handleView = async (resume: ResumeData) => {
  try {
    // 获取完整详情（包含warnings）
    const detail = await getResumeDetail(resume.id)
    currentResume.value = detail
    dialogVisible.value = true
  } catch (e) {
    // 如果获取详情失败，使用列表中的数据
    currentResume.value = resume
    dialogVisible.value = true
  }
}

const downloadSourceFile = () => {
  if (!currentResume.value?.id) return
  // 直接打开下载链接
  window.open(`${API_BASE}/api/resume/${currentResume.value.id}/file`, '_blank')
}

const previewSourceFile = async () => {
  if (!currentResume.value?.id) return

  const filename = currentResume.value.file_name || ''
  const ext = filename.split('.').pop()?.toLowerCase() || ''

  // Reset state
  previewLoading.value = true
  previewError.value = ''
  previewUrl.value = ''
  previewText.value = ''
  previewType.value = ''
  previewDialogVisible.value = true

  try {
    // Determine preview type based on file extension
    if (ext === 'pdf') {
      previewType.value = 'pdf'
      previewUrl.value = `${API_BASE}/api/resume/${currentResume.value.id}/preview`
    } else if (['jpg', 'jpeg', 'png', 'bmp', 'webp'].includes(ext)) {
      previewType.value = 'image'
      previewUrl.value = `${API_BASE}/api/resume/${currentResume.value.id}/preview`
    } else if (['docx', 'doc'].includes(ext)) {
      // DOCX/DOC 转换为 HTML 预览
      previewType.value = 'html'
      previewUrl.value = `${API_BASE}/api/resume/${currentResume.value.id}/preview`
    } else if (ext === 'txt') {
      previewType.value = 'text'
      // Fetch text content
      const response = await fetch(`${API_BASE}/api/resume/${currentResume.value.id}/preview`)
      if (!response.ok) {
        throw new Error('获取文件失败')
      }
      previewText.value = await response.text()
    } else {
      // Unsupported format
      previewError.value = `该格式(${ext})不支持在线预览，请下载查看`
    }
  } catch (e: any) {
    previewError.value = e.message || '预览失败'
  } finally {
    previewLoading.value = false
  }
}

const handleDelete = async (id: string) => {
  await ElMessageBox.confirm('确定删除这份简历？', '提示')
  await deleteResume(id)
  ElMessage.success('删除成功')
  resumes.value = resumes.value.filter(r => r.id !== id)
  selectedIds.value = selectedIds.value.filter(i => i !== id)
}

// 选择相关
const handleSelect = (id: string, selected: boolean) => {
  if (selected) {
    if (!selectedIds.value.includes(id)) {
      selectedIds.value.push(id)
    }
  } else {
    selectedIds.value = selectedIds.value.filter(i => i !== id)
  }
}

const handleSelectAll = (selected: boolean) => {
  if (selected) {
    selectedIds.value = resumes.value.map(r => r.id)
  } else {
    selectedIds.value = []
  }
}

// 批量操作
const handleBatchCommand = async (command: string) => {
  if (command === 'delete') {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 份简历？`, '批量删除')
    try {
      const result = await batchDeleteResumes(selectedIds.value)
      ElMessage.success(`成功删除 ${result.deleted} 份简历`)
      if (result.failed > 0) {
        ElMessage.warning(`${result.failed} 份删除失败`)
      }
      selectedIds.value = []
      await loadResumes()
    } catch (e) {
      ElMessage.error('批量删除失败')
    }
  } else if (command.startsWith('export-')) {
    const format = command.replace('export-', '') as 'json' | 'xml' | 'excel'
    exportResumes(format, selectedIds.value)
  }
}

// 导出
const handleExportCommand = (command: string) => {
  const format = command as 'json' | 'xml' | 'excel'
  exportResumes(format)
}

// 岗位匹配
const openMatchDialog = () => {
  matchForm.job_title = ''
  matchForm.job_description = ''
  matchForm.required_skills = []
  matchForm.preferred_skills = []
  matchForm.min_experience_years = 0
  matchForm.education_level = ''
  matchForm.use_ai = false
  matchDialogVisible.value = true
}

const handleMatch = async () => {
  if (!matchForm.job_title) {
    ElMessage.warning('请输入岗位名称')
    return
  }

  matchLoading.value = true
  try {
    const result = await batchMatchJob({
      job_title: matchForm.job_title,
      job_description: matchForm.job_description,
      required_skills: matchForm.required_skills,
      preferred_skills: matchForm.preferred_skills,
      min_experience_years: matchForm.min_experience_years,
      education_level: matchForm.education_level,
      size: 100,
      min_score: 0
    })
    matchResults.value = result.data
    matchDialogVisible.value = false
    matchResultsVisible.value = true
  } catch (e) {
    ElMessage.error('匹配失败')
  } finally {
    matchLoading.value = false
  }
}

// 学历造假风险类型标签映射
const getEducationWarningTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    fake_university: '野鸡大学',
    diploma_mill: '文凭工厂',
    degree_inflation: '学历注水',
    timeline_fraud: '时间线造假',
    overseas_fake: '海外学历造假',
    info_missing: '信息缺失',
    general: '学历风险'
  }
  return labels[type] || type
}

// 其他警告类型标签映射
const getWarningTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    // 时间相关
    time_overlap: '时间重叠',
    time_gap: '工作空档',
    time_conflict: '时间冲突',
    duration_mismatch: '任职时长异常',
    // 经历相关
    experience_exaggerated: '经历夸大',
    skill_mismatch: '技能不匹配',
    company_suspicious: '公司可疑',
    responsibility_unrealistic: '职责不实',
    // 信息缺失
    missing_contact: '缺少联系方式',
    missing_education: '缺少学历',
    missing_experience: '缺少工作经历',
    // 通用
    general: '风险提示'
  }
  return labels[type] || type
}

// 维度分析相关的辅助方法
const getScoreColorClass = (score: number): string => {
  if (score >= 90) return 'text-green-600'
  if (score >= 75) return 'text-blue-600'
  if (score >= 60) return 'text-yellow-600'
  return 'text-red-600'
}

const getScoreBarClass = (score: number): string => {
  if (score >= 90) return 'bg-green-500'
  if (score >= 75) return 'bg-blue-500'
  if (score >= 60) return 'bg-yellow-500'
  return 'bg-red-500'
}

const getLevelClass = (level: string): string => {
  const classMap: Record<string, string> = {
    '优秀': 'bg-green-100 text-green-800',
    '良好': 'bg-blue-100 text-blue-800',
    '一般': 'bg-yellow-100 text-yellow-800',
    '不足': 'bg-red-100 text-red-800'
  }
  return classMap[level] || 'bg-gray-100 text-gray-800'
}

onMounted(() => {
  loadResumes()
  // 检查是否有正在进行的批量任务，如果有则自动切换到批量上传模式
  const activeBatchId = localStorage.getItem('active_batch_id')
  if (activeBatchId) {
    uploadMode.value = 'batch'
  }
})
</script>

<style>
.resume-dialog .el-dialog__header {
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
  margin-right: 0;
}

.resume-dialog .el-dialog__body {
  padding: 24px;
  max-height: 70vh;
  overflow-y: auto;
}

.preview-dialog .el-dialog__header {
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
  margin-right: 0;
}

.preview-dialog .el-dialog__body {
  padding: 0;
  background: #f8fafc;
}

.preview-container {
  min-height: 400px;
}

.preview-container iframe {
  display: block;
}

.preview-container img {
  display: block;
  margin: 0 auto;
}

.preview-container pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
