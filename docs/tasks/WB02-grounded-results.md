# WB02 结构化代理与裁决一致性实施计划

> 执行方式：协调助手实施，独立文件并行委派，整体验收；沿用executing-plans/TDD。用户已明确要求下一步，按现有结构建议细化后直接执行，不重新询问已经确定的方向。基线9df5445；分支feat/wb02-grounded-agent-results；不推送、合并或部署。

**结果**：实现与离线验收完成，真实模型因未配置凭据而未验收；见 [交付报告](../reports/WB02.md)。

**目标**：三个代理各自有可校验的结构化结果、真实调用状态和来源引用；模型不能改变程序金额，也不能将矛盾的自由文本写入最终解释。

**设计依据**：[结构建议](../ideas/2026-10-07-structure.md) WB02。沿用FastAPI/Pydantic/requests/原生JS，不添加依赖或实时流。判断是引用与计算一致性，不宣称验证外部证据真伪。

## 设计决策

- EvidenceItem含id、case_id、source、source_path、version、value、text、observed_at、is_simulated和kind。规范输入指纹绑定版本，缺case_id用内容指纹产生inline ID。模拟来源由API样例加载路径明确传入，未知为null，不能靠case_id猜测。
- 重新从EvidenceAnalysis及规范输入建立受限事实目录，不沿用旧_gather_points中硬编码“司机称交通绕路”等表述。区分derived与reported，缺值不变为否认事实；Judge仅选derived。政策版本包含实际政策、config、本案override；明确有效等待阈值来源。
- AgentClaim含party、claims[{text,evidence_ids,policy_ids}]、missing_evidence、proposed_action。extra字段拒绝；动作枚举，缺失项限当前已知列表，每条text必须等于它唯一evidence_id对应的目录文本；引用须同案同版本、政策仅来自本案共享的确定性决策实际命中条款，并向模型提供条款全文与有效override。双方可提相反动作，不可提金额字段。Judge提议动作必须匹配最终程序动作；政策引用限最终matched_policy_ids。
- LLMResult含value、mode(llm/fallback)、status(ok/no_key/error/rejected)、model、prompt_version、latency_ms、error_code、attempts、attempt_errors。HTTP成功但解析/结构/语义不合格不算成功；仅此类错误可修复重试一次，网络错误直接fallback；错误只给固定代码，不回显异常和原始模型输出。
- Judge在风险/置信度/升级最终确定后才构造说明。发布说明为程序模板加所选已核验derived事实，强制包含最终动作/金额/升级与缺证原因；绝不发布无法验证的自由叙述。LLM模式指模型参与了结构化选择，reasoning_source明确verified_template。
- Prompt以三个带name/version/purpose的Markdown文件管理；系统模板仅接受schema和随机nonce等可信参数，所有案情放在有nonce的JSON数据块。隔离不是安全保证，输出仍需Guard；不收集或暴露私有思维链。
- 已知case_id保持不变，inline响应现在用内容指纹给出可追溯case_id；其他原API字段类型保留，增量返回evidence_catalog、policy_version、agent_results及ruling.guard/reasoning_source。每代理mode用当次结果，不能读全局最后一次健康状态推断。

## 任务与接口

### 1. 契约、目录、引用校验（协调者）
文件backend/contracts.py、backend/core/guard.py、tests/test_grounded_contracts.py。
接口：build_evidence_catalog(dispute,evidence,*,is_simulated=None)->list[EvidenceItem]；policy_version(policies,config,override)->str；build_policy_context(policies,config,dispute,evidence,decision)->dict；validate_claim(data,*,party,catalog,policy_ids,missing_evidence,expected_action=None)->dict。
- [x] 先写并运行失败用例：跨案/过期ID、真ID假文本、错ID真文本、无关政策、额外金额/说明字段、非白名单missing、unknown不伪造成否认、版本含override。
- [x] 实现严格类型与引用校验，定向测试通过。

### 2. 单次调用结果与prompt（独立模块可并行）
文件backend/core/llm.py、backend/core/prompts.py、backend/prompts/{rider,driver,judge}.md、tests/test_structured_llm.py、tests/test_prompt_boundaries.py。
接口：LLMProvider.complete_structured(system,user,*,fallback:dict,validate,prompt_version:str,max_retries:int=1)->LLMResult；render_prompt(name,data,schema)->(system,user,version)。保留complete/complete_json兼容，健康状态仅服务概况。
- [x] 先写并运行no-key/有效JSON/无效JSON/校验失败重试/超时/混合输出/异常含secret的失败测试。
- [x] 实现每次调用局部状态，最多2次HTTP，记录attempt_errors；无key不请求，mock覆盖成功/失败。
- [x] prompt测试不同调用nonce不同，恶意案情只出现在数据块，所有占位符完成替换。

### 3. 三代理集成与最终Guard（协调者）
文件agents/base.py、advocates.py、judge.py、orchestrator.py、main.py，对应tests/test_grounded_pipeline.py。
每次resolve只建一个catalog并计算一次policy decision，传入双方和Judge；代理fallback也使用相同契约。rider_case/driver_case保留argument字符串等旧字段并加structured/llm_result；ruling加agent_output/llm_result/guard/reasoning_source；顶层agent_results={rider,driver,judge}为LLMResult去掉value，trace中相关步骤meta.llm携带同一摘要。
- [x] 红→绿：恶意Judge退款动作/金额/说明不能改变结构及最终文本；缺证/低置信度升级说明不称已退款；有效0显式显示；混合三代理模式不被全局覆盖；同案变更使旧引用失效。
- [x] 保持四案原结果及/api/resolve兼容，mock三代理成功路径确实发起3次独立调用。

### 4. 模式展示与整体验收（前端可独立委派）
文件frontend/index.html、tests/frontend_behavior.cjs、tests/test_frontend.py；API新增字段如上。
- [x] 红→绿：每代理mode/model/prompt_version/attempts/error_code可见，fallback与LLM混合不被绿色总徽章盖住；缺新增字段兼容旧响应；模型字符串必须转义。
- [x] 展示最终说明由核验模板生成、引用检查状态；继续Run replay，无实时宣称。
- [x] 全量测试、四案API、真实浏览器、独立审查、报告docs/reports/WB02.md；记录真实模型是否实际验证，未配置密钥不可伪称。

## 核验与审查关注

所有离线API/pytest命令显式设OPENAI_API_KEY=与LLM_API_KEY=，避免.env补入；mock provider测试不调用收费接口。审查：多个成功/失败混合、引用版本与override、未知与缺失、升级后文本、无效输出泄漏和并发调用状态。保留0001退款7.87、0002退款5、0003及DISP-002 no_action。当前分支复用独立checkout，按既定规则仅本地提交。
