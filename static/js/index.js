// index.js : 加载并渲染 Echarts 图表
// 等待页面加载完成后出发的脚本/函数
$(function () {

    // 加载Echarts图表：左上角 排名前10的城市岗位数据 柱状图
    function initChartCityTop10() {
        // 初始化 Echarts 实例对象
        var chart_city_top10 = echarts.init(document.getElementById('chart_city_top10'), 'chalk')
        chart_city_top10.showLoading()

        // 通过 Ajax 请求获取数据
        $.get(
            'api/city_top_10', // 请求地址
            function (data) { // 请求成功后的回调函数
                chart_city_top10.hideLoading() // 隐藏加载动画

                var option = {
                    title: {
                        text: '排名前10的城市岗位数据',
                        left: 'center'
                    },
                    xAxis: {
                        type: 'category',
                        data: data.city
                    },
                    yAxis: {
                        type: 'value'
                    },
                    series: [
                        {
                            data: data.count,
                            type: 'bar',
                            showBackground: true,
                            backgroundStyle: {
                                color: 'rgba(180, 180, 180, 0.2)'
                            }
                        }
                    ],
                    tooltip: {
                        trigger: 'axis',
                        axisPointer: {
                            type: 'cross'
                        }
                    }
                };
                chart_city_top10.setOption(option)
            }
        )
    }

    initChartCityTop10()

    // 加载Echarts图表：左下角 各学历占比 饼状图
    function initChartEduLevel() {
        var chart_edu_level = echarts.init(document.getElementById('chart_edu_level'), 'chalk')
        chart_edu_level.showLoading()

        $.get(
            '/api/edu_level',
            (data) => {
                chart_edu_level.hideLoading()
                var option = {
                    title: {
                        text: '各学历占比',
                        left: 'center'
                    },
                    tooltip: {
                        trigger: 'item'
                    },
                    legend: {
                        orient: 'vertical',
                        left: 'left',
                        top: 'center'
                    },
                    series: [
                        {
                            name: '学历占比',
                            type: 'pie',
                            radius: '50%',
                            data: data,
                            emphasis: {}
                        }
                    ]
                }
                chart_edu_level.setOption(option)
            }
        )
    }

    initChartEduLevel()

    // 加载Echarts图表：中间 城市薪资区间 堆叠折线图
    function initChartSalaryRange() {
        var chart_salary_range = echarts.init(document.getElementById('chart_salary_range'), 'chalk')
        chart_salary_range.showLoading()
        $.get(
            '/api/salary_range',
            (data) => {
                chart_salary_range.hideLoading()

                var option = {
                    title: {
                        text: '各城市薪资区间',
                        left: 'center'
                    },
                    tooltip: {
                        trigger: 'axis',
                        axisPointer: {
                            type: 'cross',
                            label: {
                                backgroundColor: '#6a7985'
                            }
                        }
                    },
                    legend: {
                        data: ['最低薪资', '最高薪资'],
                        orient: 'vertical',
                        left: 'right',
                        top: 'center'
                    },
                    xAxis: {
                        type: 'category',
                        data: data.city
                    },
                    yAxis: [
                        {
                            type: 'value'
                        }
                    ],
                    series: [
                        {
                            name: '最低薪资',
                            type: 'line',
                            stack: 'Total',
                            areaStyle: {},
                            emphasis: {
                                focus: 'series'
                            },
                            data: data.salary_min
                        },
                        {
                            name: '最高薪资',
                            type: 'line',
                            stack: 'Total',
                            areaStyle: {},
                            emphasis: {
                                focus: 'series'
                            },
                            data: data.salary_max
                        }
                    ],
                    dataZoom: [
                        {
                            id: 'dataZoomX',
                            type: 'slider',
                            xAxisIndex: [0],
                            filterMode: 'filter'
                        },
                    ]
                }
                chart_salary_range.setOption(option)
            }
        )
    }

    initChartSalaryRange()


})