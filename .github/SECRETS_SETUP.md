# GitHub Secrets 配置指南

## 为什么需要配置 Secrets？

CD（持续部署）工作流需要访问 Google Cloud Platform 来部署应用。为了安全起见，我们使用 GitHub Secrets 来存储敏感信息。

## ⚠️ 当前状态

如果你看到以下错误：
```
Error: google-github-actions/auth failed with: the GitHub Action workflow must specify exactly one of "workload_identity_provider" or "credentials_json"!
```

这表示 `GCP_SA_KEY` secret 还没有配置。**这是正常的！**

CI 工作流（代码质量检查、测试、安全扫描）会继续正常运行。只有 CD 工作流（部署）会跳过。

## 📋 需要配置的 Secrets

### 1. `GCP_PROJECT_ID`
- **说明：** Google Cloud 项目 ID
- **示例：** `smart-fhir-app-prod`
- **如何获取：** 
  1. 前往 [Google Cloud Console](https://console.cloud.google.com)
  2. 选择或创建项目
  3. 项目 ID 显示在顶部导航栏

### 2. `GCP_SA_KEY`
- **说明：** Google Cloud Service Account JSON 密钥
- **格式：** JSON（完整的 service account key 文件内容）
- **如何获取：** 参见下方详细步骤

---

## 🔧 配置步骤

### 步骤 1：创建 Google Cloud 项目

1. 前往 [Google Cloud Console](https://console.cloud.google.com)
2. 创建新项目或选择现有项目
3. 记下项目 ID（例如：`smart-fhir-app-prod`）

### 步骤 2：创建 Service Account

```bash
# 设置项目 ID
export PROJECT_ID="your-project-id"

# 创建 service account
gcloud iam service-accounts create github-actions-deployer \
    --display-name="GitHub Actions Deployer" \
    --project=$PROJECT_ID

# 获取 service account email
export SA_EMAIL="github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
```

### 步骤 3：授予权限

```bash
# 授予 App Engine 管理权限
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/appengine.appAdmin"

# 授予 Cloud Build 权限
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudbuild.builds.editor"

# 授予 Storage 权限
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectAdmin"

# 授予 Service Account User 权限
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser"
```

### 步骤 4：创建密钥文件

```bash
# 创建并下载密钥
gcloud iam service-accounts keys create ~/gcp-key.json \
    --iam-account=$SA_EMAIL \
    --project=$PROJECT_ID

# 查看密钥内容
cat ~/gcp-key.json
```

⚠️ **重要：** 保管好这个密钥文件！不要提交到 Git 仓库！

### 步骤 5：在 GitHub 配置 Secrets

1. 前往你的 GitHub 仓库
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **"New repository secret"**

#### 添加 `GCP_PROJECT_ID`：
- **Name:** `GCP_PROJECT_ID`
- **Value:** 你的项目 ID（例如：`smart-fhir-app-prod`）
- 点击 **"Add secret"**

#### 添加 `GCP_SA_KEY`：
- **Name:** `GCP_SA_KEY`
- **Value:** 完整的 `gcp-key.json` 文件内容
  ```json
  {
    "type": "service_account",
    "project_id": "your-project-id",
    "private_key_id": "...",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
    ...
  }
  ```
- 点击 **"Add secret"**

### 步骤 6：验证配置

配置完成后：

1. 推送代码到 `PRECISE-HBR` 分支
2. 前往 **Actions** 标签页
3. CD 工作流应该会显示：
   - ✅ "Deployment secrets are configured"
   - 开始执行部署步骤

---

## 🔍 验证 Secrets 是否配置正确

### 检查 Secret 是否存在

在仓库的 Settings → Secrets and variables → Actions 页面，你应该看到：
- ✅ `GCP_PROJECT_ID`
- ✅ `GCP_SA_KEY`

### 查看工作流日志

在 Actions 标签页中，查看 CD 工作流的日志：

**如果 Secret 未配置：**
```
⚠️ GCP_SA_KEY secret is not configured
⚠️ Skipping deployment - please configure secrets in repository settings
```

**如果 Secret 已配置：**
```
✅ Deployment secrets are configured
Authenticating to Google Cloud...
```

---

## 🚨 常见问题

### Q: 我看到错误 "the GitHub Action workflow must specify exactly one of..."

**A:** 这是因为 `GCP_SA_KEY` secret 还没有配置。按照上述步骤配置即可。

### Q: 我配置了 Secret，但工作流还是跳过部署

**A:** 检查以下几点：
1. Secret 名称是否正确（区分大小写）
2. JSON 格式是否完整（包括开头的 `{` 和结尾的 `}`）
3. 是否有多余的空格或换行
4. 重新运行工作流（可能需要新的提交触发）

### Q: 如何更新 Secret？

**A:** 
1. 前往 Settings → Secrets and variables → Actions
2. 点击 Secret 名称旁边的 **"Update"**
3. 输入新值
4. 点击 **"Update secret"**

### Q: 我不想部署到 Google Cloud，可以跳过吗？

**A:** 可以！不配置 Secrets 即可。CI 工作流（代码质量、测试、安全扫描）会正常运行，只有 CD 部署工作流会跳过。

---

## 🔐 安全最佳实践

1. **永远不要在代码中硬编码敏感信息**
2. **不要将密钥文件提交到 Git**
3. **定期轮换 Service Account 密钥（建议每 90 天）**
4. **使用最小权限原则**
5. **监控 Service Account 的使用情况**

### 轮换密钥

```bash
# 创建新密钥
gcloud iam service-accounts keys create ~/new-gcp-key.json \
    --iam-account=$SA_EMAIL

# 更新 GitHub Secret

# 删除旧密钥
gcloud iam service-accounts keys list \
    --iam-account=$SA_EMAIL
gcloud iam service-accounts keys delete [KEY_ID] \
    --iam-account=$SA_EMAIL
```

---

## 📚 相关文档

- [Google Cloud IAM 文档](https://cloud.google.com/iam/docs)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [完整 CI/CD 设置指南](../docs/guides/CI_CD_SETUP_GUIDE.md)

---

## 🆘 需要帮助？

如果遇到问题：
1. 检查本文档的常见问题部分
2. 查看工作流日志获取详细错误信息
3. 参考 [CI/CD 设置指南](../docs/guides/CI_CD_SETUP_GUIDE.md)
4. 在 GitHub Issues 中提问

---

**最后更新：** 2025年10月28日

