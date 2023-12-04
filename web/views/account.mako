 <%
import arrow
%>
 <div class="container">
    <h6>Account View</h6>
        <div class="main">
            <div id="chart" style="height: 250px;"></div>
        </div>

        
        <div class="main">
            <p></p>
            <h6>Account Stats</h6>
            <table id="fullon" class="display compact table-striped table-bordered" style="width:100%"> 
                <thead>
                    <tr>
                        <th>Exchange</th> 
                        <th>Currency</th>                            
                        <th>First Log</th>
                        <th>Starting Balance</th>
                        <th>Last Log</th>
                        <th>Current Balance</th>
                        <th>Roi</th>
                    </tr>

                </thead>
                <tbody>
                    <tr>
                        <td>${ov.name}</td>
                        <td>${ov.currency}</td>
                        <td>${ov.fts}</td>
                        <td>${round(ov.first, 4)}</td>
                        <td>${ov.lts}</td>
                        <td>${round(ov.last, 4)}</td>
                        <%
                            flag="secondary"
                            if ov.roi != 0:
                                if ov.roi < 0:
                                    flag = "danger"
                                elif ov.roi > 0:
                                    flag = "success"
                        %>
                        <td><p class="text-${flag}">${ov.roi}%</p></td>
                    </tr>
                </tbody>
            </table>

        </div>

        

        <div class="main">
           <p></p>

           <h6>Linked Bots</h6>


            <%
                if bots == []:
                    escape = "<!-- div>"
                    close = "</div-->" 
                    mesg = '<p class="text-white">No Bots found!!</p>'
                else:
                    escape = ""
                    close = ""
                    mesg =''                 


            %>
                ${mesg}
                ${escape}
                <table id="fullon" class="display compact table-striped table-bordered" style="width:100%"> 
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Symbol</th>
                            <th>Exchange</th>
                            <th>Strategy</th>
                            <th>Leverage</th>
                            <th>Currency</th>
                            <th>Started</th>
                        </tr>

                    </thead>
                    <tbody>
                        % for bot in bots:
                        <tr>
                            <td>${bot.name}</td>
                            <td>${bot.symbol}</td>
                            <td>${bot.ex_name}</td>
                            <td>${bot.str_name}</td>
                            <td>${bot.leverage}</td>
                            <td>${bot.base}</td>
                            <td>${arrow.get(bot.timestamp).format('YYYY-MM-DD HH:mm:ss')}</td>
                        </tr>
                        % endfor
                    </tbody>
                </table>
                ${close}

        </div>

</div>

<script>
new Morris.Line({
  // ID of the element in which to draw the chart.
  element: 'chart',
  // Chart data records -- each entry in this array corresponds to a point on
  // the chart.
  data: [
        ${chart}
  ],
  // The name of the data record attribute that contains x-values.
  xkey: 'week',
  // A list of names of data record attributes that contain y-values.
  ykeys: ['balance'],
  // Labels for the ykeys -- will be displayed when you hover over the
  // chart.
  //labels: ['Value']
  pointSize: 0
});
</script>