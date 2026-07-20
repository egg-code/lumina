document.addEventListener('DOMContentLoaded', () => {
    // --- State ---
    const state = {
        step: 'upload', // 'upload', 'matches', 'sprint', 'jobs'
        maxStep: 1,
        inputMode: 'upload', // 'upload', 'paste'
        cvFile: null,
        cvText: '',
        matches: [],
        selectedMatchIndex: 0,
        dayChecks: {}, // "d1t1": true
        filters: { location: 'all', remoteOnly: false },
        currentSkillGapData: null,
        gapLoaderTimer: null,
        feedbackRating: 0
    };

    // --- DOM Elements ---
    const els = {
        // Nav
        stepPills: document.querySelectorAll('.step-pill'),
        sections: document.querySelectorAll('.step-section'),

        // Upload Step
        inputTabs: document.querySelectorAll('.input-tab'),
        inputModes: document.querySelectorAll('.input-mode'),
        dropzone: document.getElementById('dropzone'),
        cvFileInput: document.getElementById('cv-file'),
        fileNameDisplay: document.getElementById('file-name-display'),
        dropText: document.querySelector('.drop-text'),
        dropIcon: document.querySelector('.drop-icon'),
        cvTextarea: document.getElementById('cv-text'),
        useSampleBtn: document.getElementById('use-sample-btn'),
        btnFindMatches: document.getElementById('btn-find-matches'),
        uploadError: document.getElementById('upload-error'),



        analyzingCard: document.getElementById('analyzing-card'),
        analyzingStatus: document.getElementById('analyzing-status'),
        analyzingSteps: [
            document.getElementById('analyzing-step-1'),
            document.getElementById('analyzing-step-2'),
            document.getElementById('analyzing-step-3')
        ],

        // Matches Step
        matchesContainer: document.getElementById('matches-container'),
        customRoleWrap: document.getElementById('customRoleWrap'),
        customRoleInput: document.getElementById('customRoleInput'),
        customRoleBtn: document.getElementById('customRoleBtn'),

        // Skills Step
        skillsHeading: document.getElementById('skillsHeading'),
        skillsSubheading: document.getElementById('skillsSubheading'),
        readinessBanner: document.getElementById('readinessBanner'),
        readinessPill: document.getElementById('readinessPill'),
        readinessHours: document.getElementById('readinessHours'),
        
        segCv: document.getElementById('segCv'),
        segOverlap: document.getElementById('segOverlap'),
        segGap: document.getElementById('segGap'),
        legCv: document.getElementById('legCv'),
        legOverlap: document.getElementById('legOverlap'),
        legGap: document.getElementById('legGap'),

        gapLoader: document.getElementById('gapLoader'),
        gapLoaderText: document.getElementById('gapLoaderText'),
        
        existingCount: document.getElementById('existingCount'),
        overlapCount: document.getElementById('overlapCount'),
        developCount: document.getElementById('developCount'),
        existingChips: document.getElementById('existingChips'),
        overlapChips: document.getElementById('overlapChips'),
        developChips: document.getElementById('developChips'),
        
        experienceSection: document.getElementById('experienceSection'),
        experienceCount: document.getElementById('experienceCount'),
        experienceRows: document.getElementById('experienceRows'),
        experienceSkeleton: document.getElementById('experienceSkeleton'),
        
        learningSection: document.getElementById('learningSection'),
        learningItems: document.getElementById('learningItems'),
        learningSkeleton: document.getElementById('learningSkeleton'),
        showMoreLearning: document.getElementById('showMoreLearning'),
        
        backToMatchesBtn: document.getElementById('backToMatchesBtn'),
        //btnBuildSprint: document.getElementById('btn-build-sprint'),
        btnEditCv: document.getElementById('btn-edit-cv'),

        btnGoFeedback: document.getElementById('btn-go-feedback'),

        // Feedback Step
        feedbackFormWrap: document.getElementById('feedback-form-wrap'),
        feedbackSuccess: document.getElementById('feedback-success'),
        backToSkillsBtn: document.getElementById('backToSkillsBtn'),
        fbName: document.getElementById('fb-name'),
        fbEmail: document.getElementById('fb-email'),
        fbFeedback: document.getElementById('fb-feedback'),
        fbRemarks: document.getElementById('fb-remarks'),
        starRating: document.getElementById('starRating'),
        stars: document.querySelectorAll('#starRating .star'),
        feedbackError: document.getElementById('feedback-error'),
        btnSubmitFeedback: document.getElementById('btn-submit-feedback'),
        btnFeedbackDone: document.getElementById('btn-feedback-done'),

        // Sprint Step
        sprintTitle: document.getElementById('sprint-title'),
        btnViewJobs: document.getElementById('btn-view-jobs'),
        sprintDone: document.getElementById('sprint-done'),
        sprintTotal: document.getElementById('sprint-total'),
        sprintProgressBar: document.getElementById('sprint-progress-bar'),
        sprintDaysContainer: document.getElementById('sprint-days-container'),

        // Jobs Step
        filterLocation: document.getElementById('filter-location'),
        filterRemote: document.getElementById('filter-remote'),
        jobsCount: document.getElementById('jobs-count'),
        jobsList: document.getElementById('jobs-list'),
    };

    const SAMPLE_CV = "Marketing coordinator with 4 years of experience running paid social campaigns and reporting on performance in Excel and SQL. Recently completed a part-time coding bootcamp covering JavaScript, React, and databases. Built and deployed two personal projects — a budgeting app and a portfolio site — on Vercel. Comfortable with Git, basic scripting, and cross-functional communication from client-facing work.";

    // --- Helpers ---
    function getScoreColor(score) {
        if (score >= 80) return '#22C55E';
        if (score >= 60) return '#0F766E';
        return '#F97316';
    }

    function getScoreLabel(score) {
        if (score >= 80) return 'Strong match';
        if (score >= 60) return 'Good match';
        return 'Consider carefully';
    }

    function getLogoColor(company) {
        const colors = ['#0F766E', '#0B5A54', '#64748B', '#F59E0B', '#3B82F6', '#8B5CF6'];
        let hash = 0;
        for (let i = 0; i < company.length; i++) hash = company.charCodeAt(i) + ((hash << 5) - hash);
        return colors[Math.abs(hash) % colors.length];
    }

    function showError(msg) {
        els.uploadError.textContent = msg;
        setTimeout(() => { els.uploadError.textContent = ''; }, 5000);
    }

    // --- Render Functions ---

    function renderNav() {
        const stepOrder = ['upload', 'matches', 'skills', 'feedback', 'sprint', 'jobs'];
        const currentIdx = stepOrder.indexOf(state.step) + 1;

        els.stepPills.forEach((pill, idx) => {
            const stepNum = idx + 1;
            pill.className = 'step-pill';
            if (stepOrder[idx] === state.step) {
                pill.classList.add('active');
            } else if (stepNum < currentIdx) {
                pill.classList.add('done');
            }
            if (stepNum <= state.maxStep) {
                pill.classList.add('clickable');
                pill.onclick = () => goStep(stepOrder[idx]);
            } else {
                pill.onclick = null;
            }
        });

        els.sections.forEach(sec => {
            sec.style.display = sec.id === `step-${state.step}` ? 'block' : 'none';
        });
    }

    function renderUpload() {
        els.inputTabs.forEach(t => t.classList.remove('active'));
        els.inputModes.forEach(m => m.classList.remove('active'));
        
        document.querySelector(`.input-tab[data-tab="${state.inputMode}"]`).classList.add('active');
        document.getElementById(`mode-${state.inputMode}`).style.display = 'block';
        document.getElementById(`mode-${state.inputMode === 'upload' ? 'paste' : 'upload'}`).style.display = 'none';

        if (state.cvFile) {
            els.fileNameDisplay.textContent = `📄 ${state.cvFile.name}`;
            els.fileNameDisplay.style.display = 'flex';
            els.dropText.style.display = 'none';
            els.dropIcon.style.display = 'none';
        } else {
            els.fileNameDisplay.style.display = 'none';
            els.dropText.style.display = 'block';
            els.dropIcon.style.display = 'flex';
        }

        const canProceed = state.cvFile || state.cvText.trim().length > 20;
        els.btnFindMatches.disabled = !canProceed;
    }

    function renderMatches() {
        els.matchesContainer.innerHTML = '';
        state.matches.forEach((m, idx) => {
            const color = getScoreColor(m.match_score_percent);
            const card = document.createElement('div');
            card.className = 'match-card';
            
            const liveJobCount = m.live_jobs ? m.live_jobs.length : 0;
            const companyDisplay = liveJobCount > 0 ? `${liveJobCount} live openings` : m.category;
            const logoColor = getLogoColor(m.title);

            card.innerHTML = `
                <div class="match-header">
                    <div class="match-icon" style="background:${logoColor}">${m.title.charAt(0).toUpperCase()}</div>
                    <div>
                        <div class="match-title">${m.title}</div>
                        <div class="match-category">${companyDisplay}</div>
                    </div>
                </div>
                <div>
                    <div class="match-score-row">
                        <span class="match-score-label" style="color:${color}">${getScoreLabel(m.match_score_percent)}</span>
                        <span class="match-score-val" style="color:${color}">${m.match_score_percent}%</span>
                    </div>
                    <div class="match-score-bar-bg">
                        <div class="match-score-bar-fill" style="background:${color}; width:${m.match_score_percent}%"></div>
                    </div>
                </div>
                <p class="match-reasoning">${m.why_fit || `You share ${m.existing_skills.length} core skills for this role, though you'll need to brush up on ${m.missing_skills.length} missing areas.`}</p>
                <div class="match-note">${m.existing_skills.length} of ${m.existing_skills.length + m.missing_skills.length} required skills already on your CV.</div>
                <button class="btn-start-sprint" data-idx="${idx}">See skill gap →</button>
            `;
            els.matchesContainer.appendChild(card);
        });
        
        els.customRoleWrap.style.display = 'block';

        document.querySelectorAll('.btn-start-sprint').forEach(btn => {
            btn.addEventListener('click', (e) => {
                state.selectedMatchIndex = parseInt(e.target.dataset.idx);
                state.maxStep = Math.max(state.maxStep, 3);
                
                const match = state.matches[state.selectedMatchIndex];
                fetchSkillGap(match.title, match.existing_skills, match.missing_skills);
            });
        });
    }

    const GAP_LOADER_MESSAGES = [
        "Sniffing out your overlaps…",
        "Counting up your superpowers…",
        "Peeking at what the role really needs…",
        "Drawing your little circles…",
        "Almost there, hang tight…"
    ];

    function startGapLoader() {
        if (!els.gapLoader) return;
        els.gapLoader.style.display = 'flex';
        let i = 0;
        els.gapLoaderText.textContent = GAP_LOADER_MESSAGES[0];
        clearInterval(state.gapLoaderTimer);
        state.gapLoaderTimer = setInterval(() => {
            i = (i + 1) % GAP_LOADER_MESSAGES.length;
            els.gapLoaderText.style.opacity = 0;
            setTimeout(() => {
                els.gapLoaderText.textContent = GAP_LOADER_MESSAGES[i];
                els.gapLoaderText.style.opacity = 1;
            }, 250);
        }, 2200);
    }

    function stopGapLoader() {
        if (!els.gapLoader) return;
        clearInterval(state.gapLoaderTimer);
        els.gapLoader.style.display = 'none';
    }

    async function fetchSkillGap(title, existingSkills = [], missingSkills = []) {
        state.step = 'skills';
        renderNav();
        
        // Show skeletons
        els.skillsHeading.textContent = `Analyzing gap for ${title}...`;
        els.skillsSubheading.textContent = 'Our AI is mapping your CV and experience against this role. This takes few seconds.';
        els.segCv.style.width = '0%';
        els.segOverlap.style.width = '0%';
        els.segGap.style.width = '0%';
        els.legCv.textContent = '… only on CV';
        els.legOverlap.textContent = '… overlap with role';
        els.legGap.textContent = '… to build';
        
        els.existingChips.innerHTML = '';
        els.overlapChips.innerHTML = '';
        els.developChips.innerHTML = '';
        els.existingCount.textContent = '0';
        els.overlapCount.textContent = '0';
        els.developCount.textContent = '0';
        
        els.experienceSection.style.display = 'none';
        els.learningSection.style.display = 'none';
        els.readinessBanner.style.display = 'none';
        
        els.experienceSkeleton.style.display = 'block';
        els.learningSkeleton.style.display = 'block';
        //els.btnBuildSprint.disabled = true;
        startGapLoader();
        
        try {
            const res = await fetch('/api/skill-gap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cv_text: state.cvText,
                    target_title: title,
                    existing_skills: existingSkills,
                    missing_skills: missingSkills
                })
            });
            
            if (!res.ok) throw new Error("Failed to fetch skill gap");
            state.currentSkillGapData = await res.json();
            renderSkills();
        } catch (err) {
            console.error(err);
            els.skillsHeading.textContent = `Error analyzing ${title}`;
            els.skillsSubheading.textContent = 'There was a problem analyzing this role. Please try again.';
            els.experienceSkeleton.style.display = 'none';
            els.learningSkeleton.style.display = 'none';
        } finally {
            stopGapLoader();
        }
    }

    function renderSkills() {
        if (!state.currentSkillGapData) return;
        
        const data = state.currentSkillGapData;
        //els.btnBuildSprint.disabled = false;
        
        els.skillsHeading.textContent = `Where you stand for ${data.target_title}`;
        els.skillsSubheading.textContent = `See what's already strong on your CV, what overlaps with ${data.target_title}, and what to build next.`;
        
        if (data.enriched_by_llm && data.readiness_label && data.readiness_label !== 'Unknown') {
            els.readinessPill.textContent = data.readiness_label;
            els.readinessHours.textContent = data.total_learning_hours_estimate ? `~${data.total_learning_hours_estimate} hours of learning to bridge gap` : '';
            els.readinessBanner.style.display = 'flex';
        } else {
            els.readinessBanner.style.display = 'none';
        }
        
        // Segmented bar
        const cvOnlySkills = data.excess_skills || [];
        const cvOnlyCount = cvOnlySkills.length;
        const overlapCountNum = data.overlapping_skills.length;
        const gapCountNum = data.missing_skills_detail.length;
        const barTotal = Math.max(cvOnlyCount + overlapCountNum + gapCountNum, 1);
        els.segCv.style.width = `${(cvOnlyCount / barTotal) * 100}%`;
        els.segOverlap.style.width = `${(overlapCountNum / barTotal) * 100}%`;
        els.segGap.style.width = `${(gapCountNum / barTotal) * 100}%`;
        els.legCv.textContent = `${cvOnlyCount} only on CV`;
        els.legOverlap.textContent = `${overlapCountNum} overlap with role`;
        els.legGap.textContent = `${gapCountNum} to build`;
        
        // Counts
        els.existingCount.textContent = cvOnlySkills.length + data.overlapping_skills.length;
        els.overlapCount.textContent = data.overlapping_skills.length;
        els.developCount.textContent = data.missing_skills_detail.length;
        
        // Chips
        els.existingChips.innerHTML = (cvOnlySkills.concat(data.overlapping_skills)).map(s => {
            const matched = data.overlapping_skills.includes(s);
            return `<span class="skill-chip${matched?' skill-chip-matched':''}"><span class="skill-chip-icon">${matched?'✓':'•'}</span> ${s}</span>`;
        }).join('');

        els.overlapChips.innerHTML = data.overlapping_skills.length
            ? data.overlapping_skills.map(s => `<span class="skill-chip skill-chip-overlap"><span class="skill-chip-icon">✓</span> ${s}</span>`).join('')
            : '<span class="skill-empty">No direct overlap yet.</span>';

        els.developChips.innerHTML = data.missing_skills_detail.length
            ? data.missing_skills_detail.map(s => `<span class="skill-chip skill-chip-develop"><span class="skill-chip-icon">↑</span> ${s.name}</span>`).join('')
            : '<span class="skill-empty">Nothing left to build!</span>';
            
        // Experience Gaps
        els.experienceSkeleton.style.display = 'none';
        if (data.experience_gaps && data.experience_gaps.length > 0) {
            els.experienceCount.textContent = data.experience_gaps.length;
            els.experienceRows.innerHTML = `
                <div class="exp-table-wrap">
                    <table class="exp-table">
                        <thead>
                            <tr>
                                <th>Role needs</th>
                                <th>You have</th>
                                <th>Bridge note</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.experience_gaps.map(g => `
                                <tr>
                                    <td>${g.role_needs}</td>
                                    <td>${g.user_has}</td>
                                    <td><span class="bridge-icon">💡</span> ${g.bridge_note}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
            els.experienceSection.style.display = 'block';
        } else {
            els.experienceSection.style.display = 'none';
        }
        
        // Learning Pathway
        els.learningSkeleton.style.display = 'none';
        if (data.recommendations && data.recommendations.length > 0) {
            els.learningItems.innerHTML = data.recommendations.map(rec => `
                <div class="learning-item">
                    <div class="learning-item-head">
                        <h3>${rec.skill_name}</h3>
                        <p>${rec.reason}</p>
                    </div>
                    <div class="learning-resources">
                        ${rec.resources.map(res => `
                            <a href="${res.url}" target="_blank" class="resource-link">
                                <div class="resource-format ${res.format}">${res.format}</div>
                                <div class="resource-title">${res.title}</div>
                                <div class="resource-meta">
                                    <span>${res.provider}</span> • <span>${res.difficulty}</span> • <span class="${res.cost.toLowerCase().includes('free') ? 'cost-free' : ''}">${res.cost}</span>
                                </div>
                            </a>
                        `).join('')}
                    </div>
                </div>
            `).join('');
            els.learningSection.style.display = 'block';
        } else {
            els.learningSection.style.display = 'none';
        }
    }

    function renderSprint() {
        if (state.matches.length === 0) return;
        const match = state.matches[state.selectedMatchIndex];
        els.sprintTitle.textContent = `Your sprint to ${match.title}`;

        // Build sprint structure
        const sprintTasks = match.archetype_sprint && match.archetype_sprint.length === 7 
            ? match.archetype_sprint 
            : Array(7).fill("Standard portfolio and application tasks.");
        
        const extraTasks = match.actionable_steps || [];

        els.sprintDaysContainer.innerHTML = '';
        let totalCheckboxes = 0;

        sprintTasks.forEach((taskDesc, i) => {
            const dayNum = i + 1;
            const milestones = [
                "Audit & foundations", "Portfolio polish", "Close the skill gap",
                "Networking push", "Applications round 1", "Interview readiness", "Momentum & follow-up"
            ];
            
            let html = `
                <div class="sprint-day-card">
                    <div class="day-badge">
                        <div class="day-badge-label">Day</div>
                        <div class="day-badge-num">${dayNum}</div>
                    </div>
                    <div class="day-content">
                        <div class="day-milestone">${milestones[i]}</div>
                        <div class="day-tasks">
            `;

            // Default task
            const id1 = `d${dayNum}t1`;
            totalCheckboxes++;
            const checked1 = state.dayChecks[id1] ? 'checked' : '';
            html += `
                <label class="task-label ${checked1}">
                    <input type="checkbox" class="task-checkbox" data-id="${id1}" ${checked1}>
                    <span class="task-text">${taskDesc}</span>
                </label>
            `;

            // Spread LLM actionable steps across the first few days
            if (i < extraTasks.length) {
                const id2 = `d${dayNum}t2`;
                totalCheckboxes++;
                const checked2 = state.dayChecks[id2] ? 'checked' : '';
                html += `
                    <label class="task-label ${checked2}">
                        <input type="checkbox" class="task-checkbox" data-id="${id2}" ${checked2}>
                        <span class="task-text"><b>Personalized:</b> ${extraTasks[i]}</span>
                    </label>
                `;
            }

            html += `
                        </div>
                    </div>
                </div>
            `;
            els.sprintDaysContainer.innerHTML += html;
        });

        const doneCount = Object.values(state.dayChecks).filter(Boolean).length;
        els.sprintTotal.textContent = totalCheckboxes;
        els.sprintDone.textContent = doneCount;
        els.sprintProgressBar.style.width = `${(doneCount / totalCheckboxes) * 100}%`;

        document.querySelectorAll('.task-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                state.dayChecks[e.target.dataset.id] = e.target.checked;
                if (e.target.checked) e.target.closest('.task-label').classList.add('checked');
                else e.target.closest('.task-label').classList.remove('checked');
                
                const doneCount = Object.values(state.dayChecks).filter(Boolean).length;
                els.sprintDone.textContent = doneCount;
                els.sprintProgressBar.style.width = `${(doneCount / totalCheckboxes) * 100}%`;
            });
        });
    }

    function renderJobs() {
        if (state.matches.length === 0) return;
        const match = state.matches[state.selectedMatchIndex];
        const jobs = match.live_jobs || [];

        // Populate location filter options based on available jobs
        const locations = new Set(jobs.map(j => j.location).filter(Boolean));
        els.filterLocation.innerHTML = '<option value="all">All locations</option>';
        locations.forEach(loc => {
            els.filterLocation.innerHTML += `<option value="${loc}">${loc}</option>`;
        });
        els.filterLocation.value = state.filters.location;

        const filtered = jobs.filter(j => {
            if (state.filters.location !== 'all' && j.location !== state.filters.location) return false;
            // Crude remote detection if job data doesn't have a specific remote flag
            const isRemote = (j.location || '').toLowerCase().includes('remote') || (j.title || '').toLowerCase().includes('remote');
            if (state.filters.remoteOnly && !isRemote) return false;
            return true;
        });

        els.jobsCount.textContent = `${filtered.length} openings`;
        els.jobsList.innerHTML = '';

        if (filtered.length === 0) {
            els.jobsList.innerHTML = `<div class="no-jobs-msg">No openings match those filters — try widening them.</div>`;
            return;
        }

        filtered.forEach(j => {
            const card = document.createElement('div');
            card.className = 'job-card';
            const logoColor = getLogoColor(j.company || j.title);
            const isRemote = (j.location || '').toLowerCase().includes('remote') || (j.title || '').toLowerCase().includes('remote');
            
            const minSal = j.min_salary ? Math.round(j.min_salary/1000)+'k' : '';
            const maxSal = j.max_salary ? Math.round(j.max_salary/1000)+'k' : '';
            const salDisplay = minSal && maxSal ? `${minSal} - ${maxSal}` : (minSal || maxSal || 'Salary undisclosed');

            card.innerHTML = `
                <div class="job-icon" style="background:${logoColor}">${(j.company || j.title).charAt(0).toUpperCase()}</div>
                <div class="job-details">
                    <div class="job-title">${j.title}</div>
                    <div class="job-meta">${j.company || 'Unknown Company'} · ${j.location || 'Location undisclosed'} · ${salDisplay}</div>
                </div>
                ${isRemote ? '<span class="job-badge-remote">Remote</span>' : ''}
                <a href="${j.job_link || '#'}" target="_blank" class="job-link">View posting ↗</a>
            `;
            els.jobsList.appendChild(card);
        });
    }

    // --- State Transitions ---

    function goStep(newStep) {
        state.step = newStep;
        renderNav();
        if (newStep === 'upload') renderUpload();
        if (newStep === 'matches') renderMatches();
        if (newStep === 'skills') renderSkills();
        if (newStep === 'sprint') renderSprint();
        if (newStep === 'jobs') renderJobs();
    }

    // --- Event Listeners ---

    els.inputTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            state.inputMode = tab.dataset.tab;
            renderUpload();
        });
    });

    els.cvTextarea.addEventListener('input', (e) => {
        state.cvText = e.target.value;
        renderUpload();
    });

    els.useSampleBtn.addEventListener('click', () => {
        state.inputMode = 'paste';
        state.cvText = SAMPLE_CV;
        els.cvTextarea.value = SAMPLE_CV;
        renderUpload();
    });

    // Live jobs step disabled — standalone ETL pipeline pending
    // els.btnViewJobs.addEventListener('click', () => { goStep('jobs'); });

    els.filterLocation.addEventListener('change', (e) => {
        state.filters.location = e.target.value;
        renderJobs();
    });

    els.filterRemote.addEventListener('change', (e) => {
        state.filters.remoteOnly = e.target.checked;
        renderJobs();
    });
    
    // Custom Role Input
    els.customRoleInput.addEventListener('input', (e) => {
        els.customRoleBtn.disabled = e.target.value.trim().length === 0;
    });
    els.customRoleBtn.addEventListener('click', () => {
        const title = els.customRoleInput.value.trim();
        if (title) {
            fetchSkillGap(title, [], []);
        }
    });
    
    // Skills Buttons
    els.backToMatchesBtn.addEventListener('click', () => {
        goStep('matches');
    });
    // els.btnBuildSprint.addEventListener('click', () => {
    //     state.maxStep = Math.max(state.maxStep, 4);
    //     goStep('sprint');
    // });
    els.btnEditCv.addEventListener('click', () => {
        goStep('upload');
    });
    // 'Find a matched job' button removed — live jobs step disabled

    // --- Feedback Step ---
    els.btnGoFeedback.addEventListener('click', () => {
        state.maxStep = Math.max(state.maxStep, 4);
        goStep('feedback');
    });

    els.backToSkillsBtn.addEventListener('click', () => {
        goStep('skills');
    });

    els.stars.forEach(star => {
        star.addEventListener('click', () => {
            state.feedbackRating = parseInt(star.dataset.value);
            renderStars();
        });
        star.addEventListener('mouseenter', () => {
            previewStars(parseInt(star.dataset.value));
        });
    });
    els.starRating.addEventListener('mouseleave', renderStars);

    function previewStars(value) {
        els.stars.forEach(s => {
            s.classList.toggle('filled', parseInt(s.dataset.value) <= value);
        });
    }

    function renderStars() {
        previewStars(state.feedbackRating);
    }

    function resetFeedbackForm() {
        els.fbName.value = '';
        els.fbEmail.value = '';
        els.fbFeedback.value = '';
        els.fbRemarks.value = '';
        state.feedbackRating = 0;
        renderStars();
        els.feedbackError.textContent = '';
        els.feedbackFormWrap.style.display = 'block';
        els.feedbackSuccess.style.display = 'none';
    }

    els.btnSubmitFeedback.addEventListener('click', () => {
        const name = els.fbName.value.trim();
        const email = els.fbEmail.value.trim();
        const feedback = els.fbFeedback.value.trim();
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!name || !email || !feedback || state.feedbackRating === 0) {
            els.feedbackError.textContent = 'Please fill in your name, email, a rating, and your feedback.';
            return;
        }
        if (!emailPattern.test(email)) {
            els.feedbackError.textContent = 'Please enter a valid email address.';
            return;
        }
        els.feedbackError.textContent = '';

        // NOTE: UI-only for now — no backend endpoint yet.
        // Once a /api/feedback endpoint exists, POST the payload here:
        const payload = {
            name,
            email,
            rating: state.feedbackRating,
            feedback,
            remarks: els.fbRemarks.value.trim()
        };
        console.log('Feedback submitted (UI-only, not yet persisted):', payload);

        els.feedbackFormWrap.style.display = 'none';
        els.feedbackSuccess.style.display = 'block';
    });

    els.btnFeedbackDone.addEventListener('click', () => {
        resetFeedbackForm();
        goStep('matches');
    });

    // CV Preview Panel removed — file text is extracted on demand when 'Find my matches' is clicked

    // File Drag & Drop
    els.dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        els.dropzone.classList.add('drag-over');
    });
    els.dropzone.addEventListener('dragleave', () => {
        els.dropzone.classList.remove('drag-over');
    });
    els.dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        els.dropzone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) {
            state.cvFile = e.dataTransfer.files[0];
            renderUpload();
        }
    });
    els.cvFileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            state.cvFile = e.target.files[0];
            renderUpload();
        }
    });
    
    // --- Analyzing overlay ---
    const analyzingMessages = [
        "Extracting your experience…",
        "Identifying your skills…",
        "Comparing against live roles…",
        "Almost there — building your matches…"
    ];
    let analyzingTimer = null;

    function startAnalyzingAnimation() {
        let i = 0;
        els.analyzingStatus.textContent = analyzingMessages[0];
        els.analyzingSteps.forEach(el => el.classList.remove('active'));
        els.analyzingSteps[0].classList.add('active');
        els.analyzingCard.style.display = 'block';

        analyzingTimer = setInterval(() => {
            i = (i + 1) % analyzingMessages.length;
            els.analyzingStatus.style.opacity = 0;
            setTimeout(() => {
                els.analyzingStatus.textContent = analyzingMessages[i];
                els.analyzingStatus.style.opacity = 1;
            }, 300);
            els.analyzingSteps.forEach(el => el.classList.remove('active'));
            els.analyzingSteps[Math.min(Math.floor(i / 1.3), 2)].classList.add('active');
        }, 3200);
    }

    function stopAnalyzingAnimation() {
        if (analyzingTimer) clearInterval(analyzingTimer);
        analyzingTimer = null;
        els.analyzingCard.style.display = 'none';
    }

    async function fetchWithTimeout(url, options, timeoutMs = 45000) {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeoutMs);
        try {
            return await fetch(url, { ...options, signal: controller.signal });
        } finally {
            clearTimeout(id);
        }
    }


    // API Call
    els.btnFindMatches.addEventListener('click', async () => {
        els.btnFindMatches.disabled = true;
        //els.btnFindMatches.textContent = 'Analyzing...';
        els.btnFindMatches.style.display = 'none';
        //document.getElementById('loadingCard').classList.remove('hidden');
        els.uploadError.textContent = '';
        startAnalyzingAnimation();


        try {
            let textToProcess = state.cvText;

            // If in upload mode and a file is selected, extract text first
            // (skip if the preview panel already extracted this file)
            if (state.inputMode === 'upload' && state.cvFile && !state.cvText) {
                const formData = new FormData();
                formData.append('file', state.cvFile);
                
                const extractRes = await fetch('/api/extract-text', {
                    method: 'POST',
                    body: formData
                });
                
                if (!extractRes.ok) throw new Error("Failed to extract text from file.");
                const extractData = await extractRes.json();
                textToProcess = extractData.text;
                state.cvText = textToProcess;
            }

            if (!textToProcess || textToProcess.trim().length < 30) {
                throw new Error("CV text too short. Please provide more detail.");
            }

            // Call Match API
            const matchRes = await fetch('/api/match-titles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cv_text: textToProcess, top_n: 3 })
            });

            if (!matchRes.ok) throw new Error("Failed to match titles.");
            const matchData = await matchRes.json();
            
            state.matches = matchData.matches;
            state.maxStep = Math.max(state.maxStep, 2);
            goStep('matches');

        } catch (err) {
            console.error(err);
            showError(err.message || "An unexpected error occurred.");
        } finally {
            stopAnalyzingAnimation();
            els.btnFindMatches.disabled = false;
            els.btnFindMatches.style.display = '';
            els.btnFindMatches.textContent = 'Find my matches →';
            //document.getElementById('loadingCard').classList.add('hidden');
        }
    });

    // Init
    renderNav();
    renderUpload();
});