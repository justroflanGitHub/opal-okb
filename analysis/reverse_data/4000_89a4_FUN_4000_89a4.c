
uint __cdecl16far
FUN_4000_89a4(int *param_1,int *param_2,uint param_3,int *param_4,uint *param_5,undefined1 *param_6,
             int param_7,int param_8)

{
  int *piVar1;
  undefined1 *puVar2;
  undefined1 uVar3;
  int iVar4;
  uint uVar5;
  undefined1 *puVar6;
  undefined2 uVar7;
  uint in_DX;
  int *piVar8;
  uint uVar9;
  uint uVar10;
  int iVar11;
  undefined1 *puVar12;
  undefined2 uVar13;
  undefined2 uVar14;
  uint unaff_DS;
  undefined2 uVar15;
  undefined4 local_12;
  undefined1 *local_8;
  uint uVar16;
  undefined1 local_4;
  
  uVar9 = 0;
  if (param_2 == (int *)0x0 && param_3 == 0) {
    param_2 = (int *)*(undefined2 *)0x2106;
    in_DX = *(uint *)0x2108;
    param_3 = in_DX;
  }
  if (param_2 != (int *)0x0 || param_3 != 0) {
    local_12 = (int *)CONCAT22(param_3,param_2);
    in_DX = param_3;
    while( true ) {
      piVar1 = local_12;
      uVar13 = (undefined2)((ulong)local_12 >> 0x10);
      piVar8 = (int *)local_12;
      if ((*local_12 == 0 && piVar8[1] == 0) || (0x7fff < uVar9)) break;
      local_12 = (int *)CONCAT22(uVar13,piVar8 + 2);
      iVar11 = FUN_4000_6d8a(*piVar1,piVar8[1]);
      uVar9 = uVar9 + iVar11 + 1;
    }
  }
  for (iVar11 = *(int *)0x20ea; (iVar11 != 0 && (*(char *)(iVar11 + 0x20eb) == '\0'));
      iVar11 = iVar11 + -1) {
  }
  if (iVar11 != 0) {
    uVar9 = uVar9 + iVar11 + 0xe;
  }
  if (param_7 != 0 || param_8 != 0) {
    iVar4 = FUN_4000_6d8a(param_7,param_8);
    uVar9 = uVar9 + iVar4 + 3;
  }
  if (uVar9 + 1 < 0x8000) {
    uVar13 = *(undefined2 *)0x29dc;
    *(undefined2 *)0x29dc = 0x10;
    local_8 = (undefined1 *)FUN_4000_6c34(uVar9 + 0x10);
    uVar16 = unaff_DS;
    if ((local_8 != (undefined1 *)0x0) ||
       (local_8 = (undefined1 *)FUN_4000_6c8f(uVar9 + 0x10), uVar16 = in_DX,
       in_DX != 0 || local_8 != (undefined1 *)0x0)) {
      uVar10 = uVar16;
      *(undefined2 *)0x29dc = uVar13;
      uVar13 = (undefined2)((ulong)param_4 >> 0x10);
      *param_4 = (int)local_8;
      ((int *)param_4)[1] = uVar16;
      uVar5 = (int)local_8 + 0xf;
      _local_8 = (undefined1 *)(CONCAT22(uVar16,uVar5) & 0xfffffff0);
      *param_5 = uVar5 & 0xfff0;
      ((uint *)param_5)[1] = uVar10;
      if (param_2 != (int *)0x0 || param_3 != 0) {
        local_12 = (int *)CONCAT22(param_3,param_2);
        while( true ) {
          puVar2 = _local_8;
          uVar14 = (undefined2)((ulong)local_12 >> 0x10);
          piVar8 = (int *)local_12;
          uVar10 = param_3;
          if (*local_12 == 0 && piVar8[1] == 0) break;
          uVar16 = (uint)((ulong)_local_8 >> 0x10);
          local_8 = (undefined1 *)puVar2;
          uVar15 = FUN_4000_6d54(local_8,uVar16,*local_12,piVar8[1],0);
          iVar4 = FUN_4000_8712(uVar15,param_3);
          _local_8 = (undefined1 *)CONCAT22(param_3,(undefined1 *)(iVar4 + 1));
          local_12 = (int *)CONCAT22(uVar14,piVar8 + 2);
        }
      }
      puVar2 = _local_8;
      if (iVar11 != 0) {
        uVar15 = 0;
        uVar16 = (uint)((ulong)_local_8 >> 0x10);
        local_8 = (undefined1 *)puVar2;
        uVar14 = FUN_4000_6d54(local_8,uVar16,0x29f8);
        puVar6 = (undefined1 *)FUN_4000_8712(uVar14,uVar10,uVar15);
        _local_8 = (undefined1 *)CONCAT22(uVar10,puVar6);
        local_4 = (undefined1)iVar11;
        *_local_8 = local_4;
        iVar4 = 0;
        puVar6 = puVar6 + 1;
        do {
          puVar12 = puVar6;
          if (*(char *)(iVar4 + 0x20ec) == '\0') {
            uVar3 = 0xff;
          }
          else {
            uVar3 = *(undefined1 *)(iVar4 + 0x20ec);
          }
          *puVar12 = uVar3;
          iVar4 = iVar4 + 1;
          iVar11 = iVar11 + -1;
          puVar6 = puVar12 + 1;
        } while (iVar11 != 0);
        _local_8 = (undefined1 *)CONCAT22(uVar10,puVar12 + 2);
        puVar12[1] = 0;
      }
      uVar14 = (undefined2)((ulong)_local_8 >> 0x10);
      *_local_8 = 0;
      if (param_7 != 0 || param_8 != 0) {
        local_8[1] = 1;
        local_8[2] = 0;
        FUN_4000_6d54(local_8 + 3,uVar14,param_7,param_8);
      }
      uVar10 = 0;
      _local_8 = (undefined1 *)CONCAT22(param_6._2_2_,(undefined1 *)param_6 + 1);
      puVar2 = _local_8;
      uVar14 = (undefined2)((ulong)param_1 >> 0x10);
      piVar8 = (int *)param_1;
      if (*param_1 != 0 || piVar8[1] != 0) {
        iVar11 = piVar8[2];
        iVar4 = piVar8[3];
        if (iVar11 != 0 || iVar4 != 0) {
          _local_8 = (undefined1 *)CONCAT22(param_6._2_2_,(undefined1 *)param_6 + 2);
          *puVar2 = 0x20;
        }
        uVar10 = (uint)(iVar11 != 0 || iVar4 != 0);
        local_12 = (int *)CONCAT22(uVar14,piVar8 + 2);
        while( true ) {
          puVar2 = _local_8;
          uVar15 = (undefined2)((ulong)local_12 >> 0x10);
          piVar8 = (int *)local_12;
          if (*local_12 == 0 && piVar8[1] == 0) break;
          iVar11 = FUN_4000_6d8a(*local_12,piVar8[1]);
          if (0x7d < iVar11 + uVar10) {
            *(undefined2 *)0x20dd = 7;
            *(undefined2 *)0x20e8 = 10;
            FUN_4000_6c7a(*param_4,((int *)param_4)[1]);
            return 0xffff;
          }
          uVar10 = uVar10 + iVar11;
          uVar16 = (uint)((ulong)_local_8 >> 0x10);
          local_8 = (undefined1 *)puVar2;
          uVar7 = FUN_4000_6d54(local_8,uVar16,*local_12,piVar8[1],0);
          puVar6 = (undefined1 *)FUN_4000_8712(uVar7,uVar14);
          _local_8 = (undefined1 *)CONCAT22(uVar14,puVar6);
          local_12 = (int *)CONCAT22(uVar15,piVar8 + 2);
          if (*local_12 != 0 || piVar8[3] != 0) {
            *_local_8 = 0x20;
            _local_8 = (undefined1 *)CONCAT22(uVar14,puVar6 + 1);
            uVar10 = uVar10 + 1;
          }
        }
      }
      *_local_8 = 0xd;
      *param_6 = (char)uVar10;
      return uVar9 + 1;
    }
    *(undefined2 *)0x20dd = 0xc;
    *(undefined2 *)0x20e8 = 8;
    *(undefined2 *)0x29dc = uVar13;
  }
  else {
    *(undefined2 *)0x20dd = 7;
    *(undefined2 *)0x20e8 = 10;
  }
  return 0xffff;
}

