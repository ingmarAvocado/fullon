<%
import arrow
%>

 <div class="container">
   <p></p>
    <h6>Current Accounts</h6>

        <table id="fullon" class="display compact table-striped table-bordered" style="width:100%"> 
            <thead>
                <tr>
                    <th>Exchange</th>
                    <th>Currency</th>
                    <th>Initial Funds</th>
                    <th>Started</th>
                    <th>Current Funds </th>
                    <th>Diff</th>
                    <th>%</th>
                </tr>

            </thead>
            <tbody>
                % for account in accounts:
                <tr>
                    <td>${account.name}</td>
                    <%
                    link = "account/"+account.ex_id+"/"+account.currency
                    %>
                    <td><a href='${link}'>${account.currency}</a></td>
                    <td>${account.first}</td>
                    <td>${account.fts}</td>
                    <td>${account.last}</td>
                    <td>${account.diff}</td>
                    <td>${account.change}</td>

                </tr>
                % endfor
            </tbody>
        </table>
</div>
